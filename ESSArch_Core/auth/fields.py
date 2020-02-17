from rest_framework.fields import CurrentUserDefault


class CurrentUsernameDefault(CurrentUserDefault):
    def __call__(self, serializer_field):
        return serializer_field.context['request'].user.username
