from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Room, RoomMember, Message


class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'username', 'text', 'timestamp')


class RoomMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = RoomMember
        fields = ('id', 'username', 'joined_at')


class RoomSerializer(serializers.ModelSerializer):
    host_username = serializers.CharField(source='host.username', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ('id', 'name', 'room_code', 'host_username', 'member_count', 'created_at')
        read_only_fields = ('room_code', 'host_username', 'member_count', 'created_at')

    def get_member_count(self, obj):
        return obj.members.count()


class CreateRoomSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
