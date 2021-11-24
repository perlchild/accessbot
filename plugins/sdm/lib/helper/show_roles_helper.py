from .base_show_helper import BaseShowHelper
from ..util import is_hidden, HiddenTagEnum

class ShowRolesHelper(BaseShowHelper):
    def __init__(self, bot):
        self.__bot = bot
        self.__sdm_service = bot.get_sdm_service()
        super().__init__("roles")

    def get_list(self):
        roles = self.__sdm_service.get_all_roles()
        return self.__filter_hidden_roles(roles)

    def get_line(self, item, message = ''):
        account = self.__get_account(message)
        permitted_roles = account.tags.get(self.__bot.config["USER_ROLES_TAG"])
        if self.__can_request_access(item, permitted_roles):
            if self.is_auto_approve(item):
                return r"* **" + item.name + r" (auto-approve)**" + "\n"
            return f"* {item.name}\n"
        return r"* " + self.__bot.format_strikethrough(item.name) + " (not allowed)\n"

    def is_auto_approve(self, item):
        return self.__bot.config["AUTO_APPROVE_ROLE_TAG"] in item.tags

    def __get_account(self, message):
        sender_email = self.__bot.get_sender_email(message.frm)
        return self.__sdm_service.get_account_by_email(sender_email)

    def __can_request_access(self, sdm_role, permitted_roles):
        return permitted_roles is None or sdm_role.name in permitted_roles

    def __filter_hidden_roles(self, roles):
        return [
            role
            for role in roles
            if not is_hidden(self.__bot.config, HiddenTagEnum.ROLE, role)
        ]
