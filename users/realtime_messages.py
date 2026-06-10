from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .message_payload import build_message_payload
from .models import Message


def _dispatch_message_event(expediteur_id, destinataire_id, event):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(f'user_{destinataire_id}', event)
    async_to_sync(channel_layer.group_send)(f'user_{expediteur_id}', event)


def _schedule_broadcast(send_callback):
    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(send_callback)
    else:
        send_callback()


def broadcast_message_created(message, request=None):
    """Push a new message to sender and recipient WebSocket groups."""
    message_id = message.pk

    def _send():
        try:
            fresh = Message.objects.select_related('expediteur', 'destinataire').get(pk=message_id)
        except Message.DoesNotExist:
            return

        payload = build_message_payload(fresh, request)
        event = {'type': 'message.created', 'payload': payload}
        _dispatch_message_event(fresh.expediteur_id, fresh.destinataire_id, event)

    _schedule_broadcast(_send)


def broadcast_message_deleted(message, request=None):
    """Notify both parties immediately that a message was soft-deleted."""
    try:
        fresh = Message.objects.select_related('expediteur', 'destinataire').get(pk=message.pk)
    except Message.DoesNotExist:
        return

    payload = build_message_payload(fresh, request)
    payload['type'] = 'message.deleted'
    payload['is_deleted'] = True
    event = {'type': 'message.deleted', 'payload': payload}
    _dispatch_message_event(fresh.expediteur_id, fresh.destinataire_id, event)
