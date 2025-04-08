from rest_framework.views import APIView
from rest_framework import permissions, status
from django.contrib.auth import authenticate
from timesheet_app.models import CustomUser
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from timesheet_app.utils import send_telegram_message
import random
from django.contrib.auth import update_session_auth_hash
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)



# Login 
class CustomTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            return self.generate_token_response(user)
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            return Response(
                {"message": "Username is incorrect", "status": "failure", "error": "username"},
                status=status.HTTP_404_NOT_FOUND
            )

        # If username exists but password is incorrect
        if not check_password(password, user.password):
            return Response(
                {"message": "Password is incorrect", "status": "failure", "error": "password"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {"message": "Authentication failed", "status": "failure"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    def generate_token_response(self, user):
        access_token = RefreshToken.for_user(user).access_token
    
        access_token.set_exp(lifetime=timedelta(days=2))
        
        access_token_expiry_local = timezone.localtime(timezone.now() + timedelta(seconds=access_token.lifetime.total_seconds()))

        print(access_token_expiry_local)

        response = JsonResponse({
            "message": "Login successful",
            "status": "success",
            "firstname": user.firstname,
            "username": user.username,
            "usertype": user.usertype,
            "email": user.email,
            "user_id": user.id,
            "access_token_expiry": access_token_expiry_local.strftime("%Y-%m-%d %H:%M:%S")
        })

        response.set_cookie(
            key="access_token",
            value=str(access_token),
            httponly=True,
            secure=True,
            samesite="None",
            max_age=2 * 24 * 60 * 60,  
        )
        return response

# Logout
class LogoutView(APIView):
    def post(self, request):
        response = JsonResponse({"message": "Logout successful", "status": "success"})
        
        # Remove authentication cookies by setting them to an empty value and expiring them
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    
# check auth  
class AuthCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({"message": "Authenticated", "status": "success"})

# Request Password Reset Code
class RequestPasswordResetCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username_or_email = request.data.get("username_or_email")
        try:
            user = CustomUser.objects.get(username=username_or_email)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(email=username_or_email)
            except CustomUser.DoesNotExist:
                return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

     
        verification_code = str(random.randint(100000, 999999))
        cache.set(f"reset_code_{user.id}", verification_code, timeout=600)  
        
        message = f"Your password reset verification code is: {verification_code}"
        send_telegram_message(user.chat_id, message)

        return Response({"code": verification_code, "message": "Verification code sent", "status": "success"}, status=status.HTTP_200_OK)

# Change Password
class ChangePasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            user = request.user
            current_password = request.data.get("current_password")
            new_password = request.data.get("new_password")
            confirm_password = request.data.get("confirm_password")

            if not check_password(current_password, user.password):
                return Response({"message": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({"message": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            message = "Your password has been changed successfully. If you did not make this change, please contact support."
            send_telegram_message(user.chat_id, message)

            update_session_auth_hash(request, user)  

            return Response({"message": "Password changed successfully","status":"success"}, status=status.HTTP_200_OK)

        else:
            
            username_or_email = request.data.get("username_or_email")
            verification_code = request.data.get("verification_code")
            new_password = request.data.get("new_password")
            confirm_password = request.data.get("confirm_password")
            user = CustomUser.objects.filter(email=username_or_email).first() or \
                   CustomUser.objects.filter(username=username_or_email).first()

            if not user:
                return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            stored_code = cache.get(f"reset_code_{user.id}")

            if not stored_code or str(stored_code) != str(verification_code):
                return Response({"message": "Invalid or expired verification code"}, status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({"message": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            cache.delete(f"reset_code_{user.id}")

            message = "Your password has been successfully reset. If you did not request this, contact support."
            send_telegram_message(user.chat_id, message)

            return Response({"message": "Password reset successfully","status":"success"}, status=status.HTTP_200_OK) 

# User Registration
class RegisterUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        logger.info("Received a user registration request.")  # Log request
        data = request.data
        usertype = data.get('usertype')
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        email = data.get('email')
        team = data.get('team')
        subteam = data.get('subteam')
        password = data.get('password')
        chat_id = data.get('chat_id')  
        
        username = firstname
        
        if CustomUser.objects.filter(email=email).exists():
            logger.warning(f"Registration failed: Email {email} is already in use.")
            return Response({
                "message": "Registration failed",
                "status": "failure",
                "error": "Email is already registered."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if CustomUser.objects.filter(username=username).exists():
            logger.warning(f"Registration failed: Username {username} is already in use.")
            return Response({
                "message": "Registration failed",
                "status": "failure",
                "error": "Username is already taken."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Create the user
            user = CustomUser.objects.create(
                usertype=usertype,
                firstname=firstname,
                lastname=lastname,
                email=email,
                team=team,
                subteam=subteam,
                username=username,
                password=make_password(password),
                chat_id=chat_id 
            )
            logger.info(f"User {username} registered successfully.") 
            message = f"Welcome to the Timesheet App! Your username is {username}, and your password is {password}. Please log in to the app and change your password immediately."
            send_telegram_message(chat_id, message)
            return Response({
                "message": "User registered successfully",
                "status": "success",
                "username": user.username,
                "usertype": user.usertype,
                "email": user.email,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}", exc_info=True)
            return Response({"message": "Registration failed", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
