import shortuuid
from fuzzywuzzy import fuzz

from grant_request_type import GrantRequestType
from .util import is_hidden_resource

FUZZY_MATCH_THRESHOLD = 50 # Base 100

class GrantHelper:
    def __init__(self, bot):
        self.__bot = bot
        self.__admin_ids = bot.get_admin_ids()
        self.__sdm_service = bot.get_sdm_service()

    # pylint: disable=broad-except
    def access_resource(self, message, resource_name):
        execution_id = shortuuid.ShortUUID().random(length=6)
        self.__bot.log.info("##SDM## %s GrantHelper.access_resource new access request for resource_name: %s", execution_id, resource_name)
        try:
            sdm_resource = self.__get_resource(resource_name, execution_id)
            sdm_account = self.__get_account(message)
            if self.__sdm_service.grant_exists(sdm_resource.id, sdm_account.id): # TODO Add tests for this branch
                yield "You already have access to that resource!"
                return
            yield from self.__grant_resource(message, sdm_resource, sdm_account, execution_id)
        except Exception as ex:
            self.__bot.log.error("##SDM## %s GrantHelper.access_resource access request failed %s", execution_id, str(ex))
            yield str(ex)
            # TODO Extract method for this logic
            resources = self.__sdm_service.get_all_resources()
            similar_resource = self.__fuzzy_match(resources, resource_name)
            if not similar_resource:
                self.__bot.log.error("##SDM## %s GrantHelper.access_resource there are no similar resources.", execution_id)
            else:
                self.__bot.log.error("##SDM## %s GrantHelper.access_resource similar resource found: %s", execution_id, str(similar_resource))
                yield f"Did you mean \"{similar_resource}\"?"

    def assign_role(self, message, role_name):
        execution_id = shortuuid.ShortUUID().random(length=6)
        self.__bot.log.info("##SDM## %s GrantHelper.assign_role new access request for role_name: %s", execution_id, role_name)
        try:
            sdm_role = self.__get_role(role_name)
            sdm_account = self.__get_account(message)
            if not self.__allowed_to_assign_role(role_name, sdm_account):
                yield "Sorry, you\'re not allowed to get access to this role.\nContact an admin if you want to access to this role."
                return
            yield from self.__grant_role(message, sdm_role, execution_id)
        except Exception as ex:
            self.__bot.log.error("##SDM## %s GrantHelper.assign_role access request failed %s", execution_id, str(ex))
            yield str(ex)
            # TODO Extract method for this logic
            roles = self.__sdm_service.get_all_roles()
            similar_role = self.__fuzzy_match(roles, role_name)
            if not similar_role:
                self.__bot.log.error("##SDM## %s GrantHelper.access_role there are no similar roles.", execution_id)
            else:
                self.__bot.log.error("##SDM## %s GrantHelper.access_role similar role found: %s", execution_id, str(similar_role))
                yield f"Did you mean \"{similar_role}\"?"

    @staticmethod
    def generate_grant_request_id():
        return shortuuid.ShortUUID().random(length=4)

    def __grant_resource(self, message, sdm_object, sdm_account, execution_id):
        sender_nick = self.__bot.get_sender_nick(message.frm)
        sender_email = sdm_account.email
        self.__bot.log.info("##SDM## %s GrantHelper.__grant_resource sender_nick: %s sender_email: %s", execution_id, sender_nick, sender_email)
        request_id = self.__create_grant_request(message, sdm_object, sdm_account, GrantRequestType.ACCESS_RESOURCE)
        if self.__needs_manual_approval(sdm_object) or self.__reached_max_auto_approve_uses(message.frm.person):
            yield from self.__notify_access_request_entered(sender_nick, sdm_object.name, request_id)
            self.__bot.log.debug("##SDM## %s GrantHelper.__grant_resource needs manual approval", execution_id)
            return
        self.__bot.log.info("##SDM## %s GrantHelper.__grant_resource granting access", execution_id)
        yield from self.__bot.get_approve_helper().approve(request_id, True)

    def __allowed_to_assign_role(self, role_name, sdm_account):
        if not self.__bot.config['USER_ROLES_TAG']:
            return True
        permitted_roles = sdm_account.tags.get(self.__bot.config['USER_ROLES_TAG']) if sdm_account.tags else None
        return permitted_roles and role_name in permitted_roles.split(',')

    # TODO Evaluate merging with __grant_resource
    def __grant_role(self, message, sdm_object, execution_id):
        sender_nick = self.__bot.get_sender_nick(message.frm)
        sender_email = self.__bot.get_sender_email(message.frm)
        self.__bot.log.info("##SDM## %s GrantHelper.__grant_role sender_nick: %s sender_email: %s", execution_id, sender_nick, sender_email)
        sdm_account = self.__sdm_service.get_account_by_email(sender_email)
        request_id = self.__create_grant_request(message, sdm_object, sdm_account, GrantRequestType.ASSIGN_ROLE)
        yield from self.__notify_assign_role_request_entered(sender_nick, sdm_object.name, request_id)
        self.__bot.log.debug("##SDM## %s GrantHelper.__grant_role needs manual approval", execution_id)

    def __get_resource(self, resource_name, execution_id):
        role_name = self.__bot.config['CONTROL_RESOURCES_ROLE_NAME']
        if role_name and not self.__is_resource_in_role(resource_name, role_name):
            self.__bot.log.info("##SDM## %s GrantHelper.__get_resource resource not in role %s", execution_id, role_name)
            raise Exception("Access to this resource not available via bot. Please see your strongDM admins.")
        sdm_resource = self.__sdm_service.get_resource_by_name(resource_name)
        if is_hidden_resource(self.__bot.config, sdm_resource):
            self.__bot.log.info("##SDM## %s GrantHelper.__get_resource hidden resource", execution_id)
            raise Exception("Access to this resource not available via bot. Please see your strongDM admins.")
        return sdm_resource

    def __get_role(self, role_name):
        return self.__sdm_service.get_role_by_name(role_name)

    def __get_account(self, message):
        sender_email = self.__bot.get_sender_email(message.frm)
        return self.__sdm_service.get_account_by_email(sender_email)

    def __is_resource_in_role(self, resource_name, role_name):
        sdm_resources_by_role = self.__sdm_service.get_all_resources_by_role(role_name)
        return any(r.name == resource_name for r in sdm_resources_by_role)

    def __create_grant_request(self, message, sdm_object, sdm_account, grant_request_type):
        request_id = self.generate_grant_request_id()
        self.__bot.enter_grant_request(request_id, message, sdm_object, sdm_account, grant_request_type)
        return request_id

    def __needs_manual_approval(self, sdm_resource):
        tagged_resource = self.__bot.config['AUTO_APPROVE_TAG'] is not None and self.__bot.config['AUTO_APPROVE_TAG'] in sdm_resource.tags
        return not self.__bot.config['AUTO_APPROVE_ALL'] and not tagged_resource

    def __reached_max_auto_approve_uses(self, requester_id):
        max_auto_approve_uses = self.__bot.config['MAX_AUTO_APPROVE_USES']
        if not max_auto_approve_uses:
            return False
        auto_approve_uses = self.__bot.get_auto_approve_use(requester_id)
        return auto_approve_uses >= max_auto_approve_uses

    def __notify_admins(self, message):
        admins_channel = self.__bot.config['ADMINS_CHANNEL']
        if admins_channel:
            self.__bot.send(self.__bot.build_identifier(admins_channel), message)
            return

        for admin_id in self.__admin_ids:
            self.__bot.send(admin_id, message)

    def __notify_access_request_entered(self, sender_nick, resource_name, request_id):
        team_admins = ", ".join(self.__bot.get_admins())
        yield f"Thanks {sender_nick}, that is a valid request. Let me check with the team admins: {team_admins}\n" + r"Your request id is \`" + request_id + r"\`"
        self.__notify_admins(r"Hey I have an access request from USER \`" + sender_nick + r"\` for RESOURCE \`" + resource_name + r"\`! To approve, enter: **yes " + request_id + r"**")

    def __notify_assign_role_request_entered(self, sender_nick, role_name, request_id):
        team_admins = ", ".join(self.__bot.get_admins())
        yield f"Thanks {sender_nick}, that is a valid request. Let me check with the team admins: {team_admins}\n" + r"Your request id is \`" + request_id + r"\`"
        self.__notify_admins(r"Hey I have a role assign request from USER \`" + sender_nick + r"\` for ROLE \`" + role_name + r"\`! To approve, enter: **yes " + request_id + r"**")

    def __fuzzy_match(self, term_list, searched_term):
        names = [item.name for item in term_list]
        if len(names) == 0:
            return None
        max_ratio = 0
        max_ratio_name = None
        for name in names:
            # DISCLAIMER: token_sort_ratio is CPU demanding compared to other options, like: ratio or partial_ratio
            ratio = fuzz.token_sort_ratio(name, searched_term)
            if ratio > max_ratio:
                max_ratio = ratio
                max_ratio_name = name
        return max_ratio_name if max_ratio >= FUZZY_MATCH_THRESHOLD else None
