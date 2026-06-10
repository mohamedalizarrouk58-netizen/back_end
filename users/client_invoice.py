"""Create client invoices and send repair completion emails with PDF attachment."""
from decimal import Decimal
from io import BytesIO

from django.conf import settings as django_settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.formats import date_format

from xhtml2pdf import pisa

from .models import Facture


def _money(value):
    amount = Decimal(str(value or 0))
    return f'{amount:.3f} TND'


def _format_dt(value):
    if not value:
        return '-'
    return date_format(timezone.localtime(value), 'DATETIME_FORMAT', use_l10n=True)


def compute_repair_breakdown(fiche):
    """Return invoice line amounts from the repair sheet."""
    pieces = Decimal(str(fiche.cout_pieces() or 0))
    labor = Decimal(str(fiche.cout_main_oeuvre or 0))
    society = Decimal(str(fiche.frais_societe or 0))
    additional = Decimal(str(fiche.prix_supplementaire or 0))
    total = pieces + labor + society + additional
    return {
        'montant_pieces': pieces,
        'montant_main_oeuvre': labor,
        'montant_frais_societe': society,
        'montant_supplementaire': additional,
        'montant_total': total,
    }


def compute_repair_total(fiche):
    return compute_repair_breakdown(fiche)['montant_total']


def _collect_line_items(fiche, breakdown=None):
    """Build detailed invoice lines: parts, labor, society fees, additional charges."""
    if breakdown is None:
        breakdown = compute_repair_breakdown(fiche)

    lines = []

    for demande in fiche.demandes_pieces.select_related('piece').all():
        unit_price = Decimal(str(demande.piece.prix_unitaire or 0))
        qty = Decimal(str(demande.quantite or 0))
        lines.append({
            'section': 'pieces',
            'designation': demande.piece.nom,
            'detail': f'{demande.quantite} x {_money(unit_price)}',
            'montant': unit_price * qty,
        })

    if breakdown['montant_pieces'] > 0 and not lines:
        lines.append({
            'section': 'pieces',
            'designation': 'Pièces / Matériel',
            'detail': 'Fournitures utilisées',
            'montant': breakdown['montant_pieces'],
        })

    if breakdown['montant_main_oeuvre'] > 0:
        lines.append({
            'section': 'services',
            'designation': 'Main d\'oeuvre',
            'detail': 'Travail technique',
            'montant': breakdown['montant_main_oeuvre'],
        })

    if breakdown['montant_frais_societe'] > 0:
        lines.append({
            'section': 'services',
            'designation': 'Frais de la société',
            'detail': 'Frais de service',
            'montant': breakdown['montant_frais_societe'],
        })

    if breakdown['montant_supplementaire'] > 0:
        lines.append({
            'section': 'services',
            'designation': 'Prix supplémentaire',
            'detail': 'Charges additionnelles',
            'montant': breakdown['montant_supplementaire'],
        })

    return lines


def upsert_client_facture(intervention, client, fiche):
    breakdown = compute_repair_breakdown(fiche)
    facture = Facture.objects.filter(intervention=intervention).first()
    if facture is None:
        facture = Facture(
            intervention=intervention,
            client=client,
            is_deleted=False,
        )

    facture.client = client
    facture.montant_pieces = breakdown['montant_pieces']
    facture.montant_main_oeuvre = breakdown['montant_main_oeuvre']
    facture.montant_frais_societe = breakdown['montant_frais_societe']
    facture.montant_supplementaire = breakdown['montant_supplementaire']
    facture.montant_total = breakdown['montant_total']
    facture.is_deleted = False
    facture.save()
    return facture


def _build_invoice_html(facture, fiche, client, materiel, intervention, for_pdf=False):
    breakdown = {
        'montant_pieces': Decimal(str(facture.montant_pieces or 0)),
        'montant_main_oeuvre': Decimal(str(facture.montant_main_oeuvre or 0)),
        'montant_frais_societe': Decimal(str(facture.montant_frais_societe or 0)),
        'montant_supplementaire': Decimal(str(facture.montant_supplementaire or 0)),
        'montant_total': Decimal(str(facture.montant_total or 0)),
    }
    lines = _collect_line_items(fiche, breakdown)
    total = breakdown['montant_total']
    date_facture = _format_dt(facture.date_facture)
    materiel_label = f'{materiel.type} {materiel.marque} {materiel.modele} ({materiel.numero_serie})'

    rows_html = ''
    current_section = None
    section_labels = {
        'pieces': 'Pièces / Matériel',
        'services': 'Services & Frais',
    }

    for line in lines:
        section = line.get('section')
        if section and section != current_section:
            current_section = section
            rows_html += (
                f'<tr><td colspan="3" style="padding:10px 12px;background:#e2e8f0;'
                f'font-weight:bold;font-size:11px;">{section_labels.get(section, section)}</td></tr>'
            )
        rows_html += (
            f'<tr>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">{line["designation"]}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;">{line["detail"]}</td>'
            f'<td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:600;">'
            f'{_money(line["montant"])}</td>'
            f'</tr>'
        )

    summary_rows = ''
    if breakdown['montant_pieces'] > 0:
        summary_rows += f'<tr><td>Total pièces</td><td align="right">{_money(breakdown["montant_pieces"])}</td></tr>'
    if breakdown['montant_main_oeuvre'] > 0:
        summary_rows += f'<tr><td>Main d\'oeuvre</td><td align="right">{_money(breakdown["montant_main_oeuvre"])}</td></tr>'
    if breakdown['montant_frais_societe'] > 0:
        summary_rows += f'<tr><td>Frais société</td><td align="right">{_money(breakdown["montant_frais_societe"])}</td></tr>'
    if breakdown['montant_supplementaire'] > 0:
        summary_rows += f'<tr><td>Prix supplémentaire</td><td align="right">{_money(breakdown["montant_supplementaire"])}</td></tr>'

    pdf_extra = ''
    if for_pdf:
        pdf_extra = '<style>@page { size: A4; margin: 1.5cm; }</style>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Facture #{facture.id}</title>
  {pdf_extra}
  <style>
    body {{ font-family: Helvetica, Arial, sans-serif; color: #1e293b; font-size: 12px; }}
    h1 {{ color: #145f7a; font-size: 22px; margin: 0; }}
    .header {{ border-bottom: 3px solid #145f7a; padding-bottom: 16px; margin-bottom: 24px; }}
    .badge {{ background: #145f7a; color: #fff; padding: 8px 14px; border-radius: 6px; }}
    .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th {{ background: #145f7a; color: #fff; padding: 10px 12px; text-align: left; font-size: 10px; }}
    .total {{ background: #145f7a; color: #fff; padding: 14px 18px; border-radius: 8px; text-align: right; }}
    .total-amount {{ font-size: 22px; font-weight: bold; }}
    .summary td {{ padding: 6px 0; font-size: 11px; color: #475569; }}
  </style>
</head>
<body>
  <div class="header">
    <table width="100%"><tr>
      <td><h1>Gestion MT</h1><p style="color:#64748b;">Système de Gestion de Maintenance Technique</p></td>
      <td align="right"><div class="badge"><strong>FACTURE</strong><br/>N° {str(facture.id).zfill(5)}</div></td>
    </tr></table>
  </div>

  <div class="card">
    <strong>Client</strong><br/>
    {client.nom_complet}<br/>
    {client.email or ''}<br/>
    {client.telephone or ''}
  </div>

  <div class="card">
    <strong>Équipement</strong><br/>{materiel_label}<br/>
    <strong>Intervention</strong> INT-{intervention.id}<br/>
    <strong>Date facture</strong> {date_facture}
  </div>

  <div class="card">
    <strong>Description de la panne</strong><br/>{fiche.description_panne or '-'}<br/><br/>
    <strong>Solution appliquée</strong><br/>{fiche.solution or intervention.solution_proposee or '-'}<br/><br/>
    <strong>Diagnostic</strong><br/>{intervention.diagnostic or '-'}
  </div>

  <table>
    <thead>
      <tr>
        <th>Désignation</th>
        <th>Détail</th>
        <th style="text-align:right;">Montant</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>

  <table class="summary" width="100%" style="margin-top:16px;">
    {summary_rows}
  </table>

  <div class="total" style="margin-top:20px;">
    <div>Total à payer</div>
    <div class="total-amount">{_money(total)}</div>
  </div>

  <p style="margin-top:24px;color:#64748b;font-size:11px;text-align:center;">
    Merci de votre confiance — Gestion MT
  </p>
</body>
</html>"""


def _build_email_html(facture, fiche, client, materiel, intervention):
    total = _money(facture.montant_total)
    materiel_label = f'{materiel.marque} {materiel.modele} ({materiel.numero_serie})'
    breakdown_lines = []
    if Decimal(str(facture.montant_pieces or 0)) > 0:
        breakdown_lines.append(f'<p style="margin:0;"><strong>Pièces :</strong> {_money(facture.montant_pieces)}</p>')
    if Decimal(str(facture.montant_main_oeuvre or 0)) > 0:
        breakdown_lines.append(f'<p style="margin:0;"><strong>Main d\'oeuvre :</strong> {_money(facture.montant_main_oeuvre)}</p>')
    if Decimal(str(facture.montant_frais_societe or 0)) > 0:
        breakdown_lines.append(f'<p style="margin:0;"><strong>Frais société :</strong> {_money(facture.montant_frais_societe)}</p>')
    if Decimal(str(facture.montant_supplementaire or 0)) > 0:
        breakdown_lines.append(f'<p style="margin:0;"><strong>Supplément :</strong> {_money(facture.montant_supplementaire)}</p>')
    breakdown_html = ''.join(breakdown_lines)

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f1f5f9;padding:24px;color:#0f172a;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;padding:28px;">
    <h1 style="color:#145f7a;margin:0 0 8px;">Réparation terminée</h1>
    <p>Bonjour <strong>{client.nom_complet}</strong>,</p>
    <p>Votre équipement <strong>{materiel_label}</strong> a été réparé avec succès.</p>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0 0 8px;"><strong>Panne :</strong> {fiche.description_panne or '-'}</p>
      <p style="margin:0 0 8px;"><strong>Solution :</strong> {fiche.solution or intervention.solution_proposee or '-'}</p>
      {breakdown_html}
      <p style="margin:8px 0 0;"><strong>Montant total :</strong> {total}</p>
    </div>
    <p>La facture détaillée est jointe à cet email en format PDF (facture n° {facture.id}).</p>
    <p style="color:#64748b;font-size:12px;">— Gestion MT</p>
  </div>
</body>
</html>"""


def _html_to_pdf(html_string):
    buffer = BytesIO()
    status = pisa.CreatePDF(html_string, dest=buffer, encoding='utf-8')
    if status.err:
        raise ValueError('Échec de la génération du PDF de facture.')
    return buffer.getvalue()


def send_client_repair_invoice_email(facture, fiche, client, materiel, intervention):
    if not client.email:
        raise ValueError('Le client ne possède pas une adresse email.')

    invoice_html = _build_invoice_html(facture, fiche, client, materiel, intervention, for_pdf=True)
    email_html = _build_email_html(facture, fiche, client, materiel, intervention)
    pdf_bytes = _html_to_pdf(invoice_html)

    subject = f'Réparation terminée — Facture n° {facture.id} — Gestion MT'
    plain = (
        f'Bonjour {client.nom_complet},\n\n'
        f'Votre réparation est terminée. Montant total : {_money(facture.montant_total)}.\n'
        f'La facture PDF est jointe à cet email.\n\n— Gestion MT'
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        to=[client.email],
    )
    msg.attach_alternative(email_html, 'text/html')
    msg.attach(f'facture-{facture.id}.pdf', pdf_bytes, 'application/pdf')
    msg.send(fail_silently=False)

    facture.email_client_envoye = True
    facture.date_email_client = timezone.now()
    facture.save(update_fields=['email_client_envoye', 'date_email_client'])
