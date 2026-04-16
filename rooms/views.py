from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Room, RoomMember
from .serializers import RoomSerializer, CreateRoomSerializer, RoomMemberSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_room(request):
    serializer = CreateRoomSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    room = Room.objects.create(
        name=serializer.validated_data['name'],
        host=request.user,
    )
    # Host auto-joins
    RoomMember.objects.create(user=request.user, room=room)
    return Response(RoomSerializer(room).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_room(request, room_code):
    try:
        room = Room.objects.get(room_code=room_code)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(RoomSerializer(room).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_room(request, room_code):
    try:
        room = Room.objects.get(room_code=room_code)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)

    _, created = RoomMember.objects.get_or_create(user=request.user, room=room)
    msg = 'Joined room.' if created else 'Already a member.'
    return Response({'message': msg, 'room': RoomSerializer(room).data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_rooms(request):
    memberships = RoomMember.objects.filter(user=request.user).select_related('room')
    rooms = [m.room for m in memberships]
    return Response(RoomSerializer(rooms, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def room_members(request, room_code):
    try:
        room = Room.objects.get(room_code=room_code)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)
    members = room.members.select_related('user').all()
    return Response(RoomMemberSerializer(members, many=True).data)
