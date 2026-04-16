import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import Room, Message, RoomMember


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Handles real-time chat messages in a room."""

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group = f'chat_{self.room_code}'
        self.user = self.scope.get('user', AnonymousUser())

        if isinstance(self.user, AnonymousUser) or self.user.is_anonymous:
            await self.close()
            return

        # Verify room exists
        self.room = await self.get_room()
        if not self.room:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Send chat history
        history = await self.get_chat_history()
        await self.send_json({'type': 'chat_history', 'messages': history})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('type')

        if msg_type == 'message':
            text = content.get('text', '').strip()
            if not text:
                return

            message_data = await self.save_message(text)
            await self.channel_layer.group_send(
                self.room_group,
                {
                    'type': 'chat_message',
                    'message': message_data,
                }
            )

    async def chat_message(self, event):
        await self.send_json({
            'type': 'message',
            'message': event['message'],
        })

    @database_sync_to_async
    def get_room(self):
        try:
            return Room.objects.get(room_code=self.room_code)
        except Room.DoesNotExist:
            return None

    @database_sync_to_async
    def get_chat_history(self):
        messages = Message.objects.filter(
            room=self.room
        ).select_related('user').order_by('timestamp')[:100]
        return [
            {
                'id': m.id,
                'username': m.user.username,
                'text': m.text,
                'timestamp': m.timestamp.isoformat(),
            }
            for m in messages
        ]

    @database_sync_to_async
    def save_message(self, text):
        msg = Message.objects.create(
            room=self.room,
            user=self.user,
            text=text,
        )
        return {
            'id': msg.id,
            'username': self.user.username,
            'text': msg.text,
            'timestamp': msg.timestamp.isoformat(),
        }


class SignalingConsumer(AsyncJsonWebsocketConsumer):
    """Handles WebRTC signaling: offer, answer, ice-candidate."""

    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group = f'signal_{self.room_code}'
        self.user = self.scope.get('user', AnonymousUser())

        if isinstance(self.user, AnonymousUser) or self.user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Notify others that a new peer joined
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type': 'peer_joined',
                'username': self.user.username,
                'user_id': self.user.id,
                'channel': self.channel_name,
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(
            self.room_group,
            {
                'type': 'peer_left',
                'username': self.user.username,
                'user_id': self.user.id,
            }
        )
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive_json(self, content):
        msg_type = content.get('type')
        target = content.get('target')  # target channel name or user

        if msg_type in ('offer', 'answer', 'ice-candidate'):
            # Forward signaling message to the specific target or broadcast
            payload = {
                'type': 'signaling_message',
                'signal_type': msg_type,
                'data': content.get('data'),
                'sender': self.user.username,
                'sender_id': self.user.id,
                'sender_channel': self.channel_name,
            }

            if target:
                # Send to specific channel
                await self.channel_layer.send(target, payload)
            else:
                # Broadcast to room
                await self.channel_layer.group_send(self.room_group, payload)

    async def peer_joined(self, event):
        # Don't send to the peer who just joined
        if event['channel'] != self.channel_name:
            await self.send_json({
                'type': 'peer-joined',
                'username': event['username'],
                'user_id': event['user_id'],
                'channel': event['channel'],
            })

    async def peer_left(self, event):
        if event['user_id'] != self.user.id:
            await self.send_json({
                'type': 'peer-left',
                'username': event['username'],
                'user_id': event['user_id'],
            })

    async def signaling_message(self, event):
        # Don't echo back to sender
        if event['sender_channel'] != self.channel_name:
            await self.send_json({
                'type': event['signal_type'],
                'data': event['data'],
                'sender': event['sender'],
                'sender_id': event['sender_id'],
                'sender_channel': event['sender_channel'],
            })
