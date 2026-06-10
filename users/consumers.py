from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Message
from .message_payload import build_message_payload


class MessageConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")

        if event_type == "message.send":
            await self._handle_message_send(content)
            return

        if event_type == "message.read":
            await self._handle_message_read(content)
            return

        await self.send_json({
            "type": "error",
            "detail": "Unsupported event type"
        })

    async def _handle_message_send(self, content):
        destinataire_id = content.get("destinataire")
        objet = content.get("objet", "")
        contenu = content.get("contenu", "")

        payload, error = await self._create_message(
            sender_id=self.user.id,
            destinataire_id=destinataire_id,
            objet=objet,
            contenu=contenu,
        )

        if error:
            await self.send_json({"type": "error", "detail": error})
            return

        await self.channel_layer.group_send(
            f"user_{payload['destinataire']}",
            {"type": "message.created", "payload": payload},
        )

        await self.channel_layer.group_send(
            f"user_{payload['expediteur']}",
            {"type": "message.created", "payload": payload},
        )

    async def _handle_message_read(self, content):
        message_id = content.get("id")
        payload, error = await self._build_message_read_payload(
            message_id=message_id,
            user_id=self.user.id,
        )

        if error:
            await self.send_json({"type": "error", "detail": error})
            return

        await self.channel_layer.group_send(
            f"user_{payload['expediteur']}",
            {"type": "message.read", "payload": payload},
        )
        await self.channel_layer.group_send(
            f"user_{payload['destinataire']}",
            {"type": "message.read", "payload": payload},
        )

    async def message_created(self, event):
        await self.send_json(event["payload"])

    async def message_deleted(self, event):
        await self.send_json(event["payload"])

    async def message_read(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _create_message(self, sender_id, destinataire_id, objet, contenu):
        if not destinataire_id:
            return None, "destinataire is required"

        contenu = str(contenu or '').strip()
        if not contenu:
            return None, "contenu is required for text messages. Use the API for images and voice."

        User = get_user_model()

        try:
            sender = User.objects.get(id=sender_id)
        except User.DoesNotExist:
            return None, "Invalid sender"

        try:
            destinataire = User.objects.get(id=destinataire_id)
        except User.DoesNotExist:
            return None, "Invalid destinataire"

        if getattr(destinataire, "is_deleted", False):
            return None, "Invalid destinataire"

        if destinataire.id == sender.id:
            return None, "You cannot send a message to yourself"

        message = Message.objects.create(
            expediteur=sender,
            destinataire=destinataire,
            objet=(objet or "").strip(),
            contenu=contenu,
            type_message=Message.TYPE_TEXT,
        )

        return build_message_payload(message), None

    @database_sync_to_async
    def _build_message_read_payload(self, message_id, user_id):
        if not message_id:
            return None, "id is required"

        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return None, "Message not found"

        if message.expediteur_id != user_id and message.destinataire_id != user_id:
            return None, "Forbidden"

        return {
            "type": "message.read",
            "id": message.id,
            "expediteur": message.expediteur_id,
            "destinataire": message.destinataire_id,
            "reader": user_id,
            "date": message.date_envoi.isoformat(),
        }, None
