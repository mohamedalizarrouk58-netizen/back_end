from django.conf import settings


def _absolute_media_url(url, request=None):
    if not url:
        return None
    if url.startswith('http://') or url.startswith('https://'):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    public_base = getattr(settings, 'PUBLIC_API_URL', 'http://127.0.0.1:8000').rstrip('/')
    return f'{public_base}{url}'


def _fichier_display_name(message):
    if not message.fichier:
        return None
    name = message.fichier.name or ''
    return name.rsplit('/', 1)[-1] if name else None


def build_message_payload(message, request=None):
    fichier_url = None
    if message.fichier:
        fichier_url = _absolute_media_url(message.fichier.url, request)

    return {
        'type': 'message.created',
        'id': message.id,
        'expediteur': message.expediteur_id,
        'destinataire': message.destinataire_id,
        'objet': message.objet,
        'contenu': message.contenu,
        'type_message': message.type_message,
        'fichier_url': fichier_url,
        'fichier_name': _fichier_display_name(message),
        'is_deleted': bool(message.is_deleted),
        'date_envoi': message.date_envoi.isoformat(),
    }
