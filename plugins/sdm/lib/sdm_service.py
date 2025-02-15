import strongdm

def create_sdm_service(api_access_key, api_secret_key, log):
    client = strongdm.Client(api_access_key, api_secret_key)
    return SdmService(client, log)

class SdmService:
    def __init__(self, client, log):
        self.__client = client
        self.__log = log

    def get_resource_by_name(self, name):
        """
        Return a SDM resouce by name
        """
        try:
            self.__log.debug("##SDM## SdmService.get_resource_by_name name: %s", name)
            sdm_resources = list(self.__client.resources.list('name:"{}"'.format(name)))
        except Exception as ex:
            raise Exception("List resources failed: " + str(ex)) from ex
        if len(sdm_resources) == 0:
            raise Exception("Sorry, cannot find that resource!")
        return sdm_resources[0]

    def get_account_by_email(self, email):
        """
        Return a SDM account by email
        """
        try:
            self.__log.debug("##SDM## SdmService.get_account_by_email email: %s", email)
            sdm_accounts = list(self.__client.accounts.list('email:{}'.format(email)))
        except Exception as ex:
            raise Exception("List accounts failed: " + str(ex)) from ex
        if len(sdm_accounts) == 0:
            raise Exception("Sorry, cannot find your account!")
        return sdm_accounts[0]

    def grant_exists(self, resource_id, account_id):
        """
        Does a grant exists
        """
        try:
            self.__log.debug("##SDM## SdmService.grant_exists resource_id: %s account_id: %s", resource_id, account_id)
            account_grant_iter = self.__client.account_grants.list(f"resource_id:{resource_id},account_id:{account_id}")
            return next(account_grant_iter, None) is not None
        except Exception as ex:
            raise Exception("Grant exists failed: " + str(ex)) from ex

    def grant_temporary_access(self, resource_id, account_id, start_from, valid_until):
        """
        Grant temporary access to a SDM resource for an account
        """
        try:
            self.__log.debug(
                "##SDM## SdmService.grant_temporary_access resource_id: %s account_id: %s start_from: %s valid_until: %s",
                resource_id, account_id, str(start_from), str(valid_until)
            )
            sdm_grant = strongdm.AccountGrant(
                resource_id = resource_id,
                account_id = account_id,
                start_from = start_from,
                valid_until = valid_until
            )
            self.__client.account_grants.create(sdm_grant)
        except Exception as ex:
            raise Exception("Grant failed: " + str(ex)) from ex

    def get_all_resources(self):
        """
        Return all resources
        """
        self.__log.debug("##SDM## SdmService.get_all_resources")
        try:
            return self.remove_none_values(self.__client.resources.list(''))
        except Exception as ex:
            raise Exception("List resources failed: " + str(ex)) from ex

    def get_all_resources_by_role(self, role_name):
        """
        Return all resources by role name
        """
        self.__log.debug("##SDM## SdmService.get_all_resources_by_role_name role_name: %s", role_name)
        try:
            sdm_role = self.get_role_by_name(role_name)
            sdm_role_grants = list(self.__client.role_grants.list(f"role_id:{sdm_role.id}"))
            resouces_filter = ",".join([f"id:{rg.resource_id}" for rg in sdm_role_grants])
            return self.remove_none_values(self.__client.resources.list(resouces_filter))
        except Exception as ex:
            raise Exception("List resources by role failed: " + str(ex)) from ex

    def get_role_by_name(self, name):
        """
        Return a SDM role by name
        """
        try:
            self.__log.debug("##SDM## SdmService.get_role_by_name name: %s", name)
            sdm_roles = list(self.__client.roles.list('name:"{}"'.format(name)))
        except Exception as ex:
            raise Exception("List roles failed: " + str(ex)) from ex
        if len(sdm_roles) == 0:
            raise Exception("Sorry, cannot find that role!")
        return sdm_roles[0]

    def get_all_roles(self):
        """
        Return all roles
        """
        self.__log.debug("##SDM## SdmService.get_all_roles")
        try:
            return list(self.__client.roles.list(''))
        except Exception as ex:
            raise Exception("List roles failed: " + str(ex)) from ex

    @staticmethod
    def remove_none_values(elements):
        return [e for e in elements if e is not None]
