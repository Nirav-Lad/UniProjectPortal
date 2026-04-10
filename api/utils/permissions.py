from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Allows access only to users with usertype = 'Admin'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) == 'Admin'
        )


class IsStudentUser(BasePermission):
    """
    Allows access only to users with usertype = 'Student'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) == 'Student'
        )


class IsGuideUser(BasePermission):
    """
    Allows access only to users with usertype = 'Guide'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) == 'Guide'
        )

class IsAdminOrGuideUser(BasePermission):
    """
    Allows access only to users with usertype = 'Guide' or 'Admin'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) in ['Admin','Guide']
        )
    
class IsAdminOrStudentUser(BasePermission):
    """
    Allows access only to users with usertype = 'Student' or 'Admin'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) in ['Admin','Student']
        )

class IsGuideOrStudentUser(BasePermission):
    """
    Allows access only to users with usertype = 'Student' or 'Guide'.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'usertype', None) in ['Guide','Student']
        )