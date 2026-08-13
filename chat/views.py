from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gita.serializers import ShlokaSerializer

from .ai_service import generate_gita_guidance
from .models import Conversation, Message
from .serializers import ChatRequestSerializer
from .services import find_relevant_shlokas


class ChatView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def post(self, request):

        # ==================================================
        # VALIDATE REQUEST
        # ==================================================

        serializer = ChatRequestSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        message_text = (
            serializer.validated_data["message"]
        )

        conversation_id = (
            serializer.validated_data.get(
                "conversation_id"
            )
        )

        # ==================================================
        # FIND EXISTING CONVERSATION
        # ==================================================

        if conversation_id:

            try:

                conversation = (
                    Conversation.objects.get(
                        id=conversation_id,
                        user=request.user
                    )
                )

            except Conversation.DoesNotExist:

                return Response(
                    {
                        "error":
                            "Conversation not found."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        # ==================================================
        # CREATE NEW CONVERSATION
        # ==================================================

        else:

            conversation = (
                Conversation.objects.create(
                    user=request.user,
                    title=message_text[:60]
                )
            )

        # ==================================================
        # SAVE USER MESSAGE
        # ==================================================

        user_message = Message.objects.create(
            conversation=conversation,
            role="user",
            content=message_text
        )

        # ==================================================
        # GET PREVIOUS CONVERSATION HISTORY
        # ==================================================

        previous_messages = (
            Message.objects
            .filter(
                conversation=conversation
            )
            .exclude(
                id=user_message.id
            )
            .order_by("created_at")
        )

        # --------------------------------------------------
        # Keep the most recent messages.
        #
        # This prevents the prompt from becoming enormous
        # when a conversation gets very long.
        # --------------------------------------------------

        previous_messages = list(
            previous_messages
        )[-10:]

        conversation_history = []

        for message in previous_messages:

            conversation_history.append(
                {
                    "role":
                        message.role,

                    "content":
                        message.content,
                }
            )

        # ==================================================
        # RETRIEVE RELEVANT SHLOKAS
        # ==================================================

        relevant_shlokas = (
            find_relevant_shlokas(
                message_text,
                limit=3
            )
        )

        shloka_data = ShlokaSerializer(
            relevant_shlokas,
            many=True
        ).data

        # ==================================================
        # GENERATE AI GUIDANCE
        # ==================================================

        try:

            assistant_text = (
                generate_gita_guidance(
                    user_message=message_text,
                    shlokas=relevant_shlokas,
                    conversation_history=conversation_history
                )
            )

        except Exception as error:

            return Response(
                {
                    "error":
                        "AI guidance could not be generated.",

                    "details":
                        str(error),

                    "conversation_id":
                        conversation.id,

                    "relevant_shlokas":
                        shloka_data,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # ==================================================
        # SAVE AI MESSAGE
        # ==================================================

        assistant_message = (
            Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=assistant_text
            )
        )

        # ==================================================
        # RESPONSE
        # ==================================================

        return Response(
            {
                "conversation_id":
                    conversation.id,

                "user_message": {
                    "id":
                        user_message.id,

                    "role":
                        user_message.role,

                    "content":
                        user_message.content,
                },

                "relevant_shlokas":
                    shloka_data,

                "assistant_message": {
                    "id":
                        assistant_message.id,

                    "role":
                        assistant_message.role,

                    "content":
                        assistant_message.content,
                },
            },
            status=status.HTTP_200_OK
        )