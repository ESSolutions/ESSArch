from rest_framework.fields import CurrentUserDefault


class CurrentUsernameDefault(CurrentUserDefault):
    def __call__(self):
        return self.user.username
