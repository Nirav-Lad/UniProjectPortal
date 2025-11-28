from rest_framework.views import APIView
import jwt
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import LogMaster, GroupFormation, UserMaster,TokenTracking,GuideGroup,StudentBatch,GroupStudents,StudentDetails
from ..serializers import MeetingLogCreateSerializer,MeetingLogUpdateSerializer
from rest_framework.permissions import IsAuthenticated
from ..utils.permissions import IsAdminUser, IsStudentUser, IsGuideUser


class MeetingLogCreateView(APIView):
    """
    API endpoint to create a meeting log with JWT authentication.
    Flow:
    1. Get JWT token from request headers.
    2. Validate the token and check if it exists in user_master DB.
    3. Extract user_id from the token.
    4. Validate group_id and request data.
    5. Save meeting log in DB.
    """

    def post(self, request, *args, **kwargs):
        # Step 1: Extract token from headers
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"error": "Authorization header missing or invalid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        token = auth_header.split(" ")[1]

        try:
            # Step 2: Decode token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            if not user_id:
                return Response(
                    {"error": "Invalid token, user_id missing"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Step 3: Check if token exists in DB for the user
            try:
                # user = UserMaster.objects.get(user_id=user_id, access_token=token)
                token_record = TokenTracking.objects.get(access_token=token)
                print("1111#################\n",token_record,"\n#################11111")
                user = token_record.user
                print("#################\n",user,"\n#################")
            except UserMaster.DoesNotExist:
                return Response(
                    {"error": "Invalid or expired token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except jwt.ExpiredSignatureError:
            return Response(
                {"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )

        # Step 4: Validate request body
        serializer = MeetingLogCreateSerializer(data=request.data)
        if serializer.is_valid():
            group_id = serializer.validated_data["group_id"]

            # Fetch group instance
            try:
                group = GroupFormation.objects.get(pk=group_id)
            except GroupFormation.DoesNotExist:
                return Response(
                    {"error": "Group not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Step 5: Save Meeting Log in DB
            meeting_log = LogMaster.objects.create(
                group_id_id=group.id,
                changes_suggested_prev=serializer.validated_data.get(
                    "changes_suggested_prev"
                ),
                changes_done_prev=serializer.validated_data.get("changes_done_prev"),
                suggested_changes_next=serializer.validated_data.get(
                    "suggested_changes_next"
                ),
                guide_remarks=serializer.validated_data.get("guide_remarks"),
                approval_status=False,  # default
                created_by=user,
            )

            return Response(
                {
                    "message": "Meeting log created successfully",
                    "log_id": meeting_log.log_id,
                    "group_id": group_id,
                    "created_by": user.id,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class MeetingLogListView(APIView):
    permission_classes = [IsAuthenticated]
    
    """
    API endpoint to list all meeting logs.
    """

    def get(self, request, *args, **kwargs):
        user_role = request.query_params.get("user_role")
        user_id = request.query_params.get("id")
        # guide_id = request.query_params.get("guide_id")
        print("#################\n",user_role,user_id,"\n#################")
        
        # Validate query parameters
        if user_role is None or user_id is None:
            return Response(
                {"error": "Both user_role and user_id query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
         # Convert user_id to int safely
        try:
            user_id = int(user_id)
        except ValueError:
            return Response(
                {"error": "user_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- CASE 1: GUIDE ---
        if user_role.lower() == "guide":
            guide_id = user_id
            group_ids = GuideGroup.objects.filter(guide_id=guide_id).values_list('group_id', flat=True)
            print("#################\n",group_ids,"\n#################")
            meeting_logs = LogMaster.objects.filter(group_id_id__in=group_ids)
        
        
        # --- CASE 2: STUDENT ---    
        elif user_role.lower() == "student":
            enrollment_id = user_id
            studentBatch_link = StudentBatch.objects.filter(enrollment_id=enrollment_id).first()
            print("#################\n",studentBatch_link,"\n#################")
            student_batch_link_id = studentBatch_link.id
            print("#################\n",student_batch_link_id,"\n#################")
            group_student_link = GroupStudents.objects.get(student_batch_link_id=student_batch_link_id)
            print("#################\n",group_student_link,"\n#################")
            group_id = group_student_link.group_id
            print("#################\n",group_id,"\n#################")
            # group_ids = GroupFormation.objects.filter(
            #     id=group_id
            # ).values_list("group_id", flat=True)
            # print("#################\n",group_ids,"\n#################")
            meeting_logs = LogMaster.objects.filter(group_id=group_id)

        else:
            return Response(
                {"error": "Invalid user_role. Must be 'Guide' or 'Student'."},
                status=status.HTTP_400_BAD_REQUEST
            )
         
        
        # meeting_logs = LogMaster.objects.all()
        serialized_logs = [
            {
                "log_id": log.log_id,
                "group_id": log.group_id_id,
                "changes_suggested_prev": log.changes_suggested_prev,
                "changes_done_prev": log.changes_done_prev,
                "suggested_changes_next": log.suggested_changes_next,
                "guide_remarks": log.guide_remarks,
                "approval_status": log.approval_status,
                "created_at": log.created_at,
                "created_by_id": log.created_by.id,
                "created_by_name": StudentDetails.objects.get(user_id=log.created_by.id).name,
            }
            for log in meeting_logs
        ]
        return Response(serialized_logs, status=status.HTTP_200_OK)
    
class MeetingLogApproveView(APIView):
    """
    API endpoint to approve a meeting log.
    """

    def put(self, request, *args, **kwargs):
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                {"error": "Authorization header missing or invalid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        token = auth_header.split(" ")[1]
        
        try:
            # Step 2: Decode token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            if not user_id:
                return Response(
                    {"error": "Invalid token, user_id missing"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Step 3: Check if token exists in DB for the user
            try:
                # user = UserMaster.objects.get(user_id=user_id, access_token=token)
                token_record = TokenTracking.objects.get(access_token=token)
                print("1111#################\n",token_record,"\n#################11111")
                user = token_record.user
                print("#################\n",user,"\n#################")
            except UserMaster.DoesNotExist:
                return Response(
                    {"error": "Invalid or expired token"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except jwt.ExpiredSignatureError:
            return Response(
                {"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )
        # Step 4: Validate request body & approve log
        
        serializer = MeetingLogUpdateSerializer(data=request.data)
        if serializer.is_valid():
            log_id = serializer.validated_data["log_id"]
            
            try:
                meeting_log = LogMaster.objects.get(log_id=log_id)
                meeting_log.approval_status = True
                meeting_log.guide_remarks = serializer.validated_data.get("guide_remarks")
                meeting_log.changes_suggested_prev = serializer.validated_data.get("changes_suggested_prev")
                meeting_log.changes_done_prev = serializer.validated_data.get("changes_done_prev")
                meeting_log.suggested_changes_next = serializer.validated_data.get("suggested_changes_next")
                meeting_log.save()
                
                return Response(
                    {"message": "Meeting log approved successfully"},
                    status=status.HTTP_200_OK,
                )
            except LogMaster.DoesNotExist:
                return Response(
                    {"error": "Meeting log not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
        else:
            return Response(
                {"error": "Log data invalid", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
class GroupListView(APIView):
    """
    API endpoint to list all groups under a specific guide.
    """

    def get(self, request, *args, **kwargs):
        guide_id = request.query_params.get("guide_id")
        if not guide_id:
            return Response(
                {"error": "guide_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group_ids = GuideGroup.objects.filter(guide_id=guide_id)
        print("#################\n",group_ids,"\n#################")
        groups_list = {}
        for gid in group_ids:
            groups_list[gid] = GroupFormation.objects.get(pk=gid)
            
            # print("#################\n",gid.group_id,"\n#################")
        # serialized_groups = [
        #     {
        #         "group_id": group.id,
        #         "group_name": group.group_name,
        #         "created_at": group.created_at,
        #     }
        #     for group in groups
        # ]
        return Response(groups_list, status=status.HTTP_200_OK)

        
        
        