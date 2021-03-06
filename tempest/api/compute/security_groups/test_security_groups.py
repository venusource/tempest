# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.api.compute.security_groups import base
from tempest.common.utils import data_utils
from tempest import exceptions
from tempest import test


class SecurityGroupsTestJSON(base.BaseSecurityGroupsTest):

    @classmethod
    def resource_setup(cls):
        super(SecurityGroupsTestJSON, cls).resource_setup()
        cls.client = cls.security_groups_client

    @test.attr(type='smoke')
    @test.services('network')
    def test_security_groups_create_list_delete(self):
        # Positive test:Should return the list of Security Groups
        # Create 3 Security Groups
        security_group_list = []
        for i in range(3):
            resp, body = self.create_security_group()
            self.assertEqual(200, resp.status)
            security_group_list.append(body)
        # Fetch all Security Groups and verify the list
        # has all created Security Groups
        resp, fetched_list = self.client.list_security_groups()
        self.assertEqual(200, resp.status)
        # Now check if all the created Security Groups are in fetched list
        missing_sgs = \
            [sg for sg in security_group_list if sg not in fetched_list]
        self.assertFalse(missing_sgs,
                         "Failed to find Security Group %s in fetched "
                         "list" % ', '.join(m_group['name']
                                            for m_group in missing_sgs))
        # Delete all security groups
        for sg in security_group_list:
            resp, _ = self.client.delete_security_group(sg['id'])
            self.assertEqual(202, resp.status)
            self.client.wait_for_resource_deletion(sg['id'])
        # Now check if all the created Security Groups are deleted
        resp, fetched_list = self.client.list_security_groups()
        deleted_sgs = \
            [sg for sg in security_group_list if sg in fetched_list]
        self.assertFalse(deleted_sgs,
                         "Failed to delete Security Group %s "
                         "list" % ', '.join(m_group['name']
                                            for m_group in deleted_sgs))

    @test.attr(type='smoke')
    @test.services('network')
    def test_security_group_create_get_delete(self):
        # Security Group should be created, fetched and deleted
        # with char space between name along with
        # leading and trailing spaces
        s_name = ' %s ' % data_utils.rand_name('securitygroup ')
        resp, securitygroup = self.create_security_group(name=s_name)
        self.assertEqual(200, resp.status)
        self.assertIn('name', securitygroup)
        securitygroup_name = securitygroup['name']
        self.assertEqual(securitygroup_name, s_name,
                         "The created Security Group name is "
                         "not equal to the requested name")
        # Now fetch the created Security Group by its 'id'
        resp, fetched_group = \
            self.client.get_security_group(securitygroup['id'])
        self.assertEqual(200, resp.status)
        self.assertEqual(securitygroup, fetched_group,
                         "The fetched Security Group is different "
                         "from the created Group")
        resp, _ = self.client.delete_security_group(securitygroup['id'])
        self.assertEqual(202, resp.status)
        self.client.wait_for_resource_deletion(securitygroup['id'])

    @test.attr(type='smoke')
    @test.services('network')
    def test_server_security_groups(self):
        # Checks that security groups may be added and linked to a server
        # and not deleted if the server is active.
        # Create a couple security groups that we will use
        # for the server resource this test creates
        resp, sg = self.create_security_group()
        resp, sg2 = self.create_security_group()

        # Create server and add the security group created
        # above to the server we just created
        server_name = data_utils.rand_name('server')
        resp, server = self.create_test_server(name=server_name)
        server_id = server['id']
        self.servers_client.wait_for_server_status(server_id, 'ACTIVE')
        resp, body = self.servers_client.add_security_group(server_id,
                                                            sg['name'])

        # Check that we are not able to delete the security
        # group since it is in use by an active server
        self.assertRaises(exceptions.BadRequest,
                          self.client.delete_security_group,
                          sg['id'])

        # Reboot and add the other security group
        resp, body = self.servers_client.reboot(server_id, 'HARD')
        self.servers_client.wait_for_server_status(server_id, 'ACTIVE')
        resp, body = self.servers_client.add_security_group(server_id,
                                                            sg2['name'])

        # Check that we are not able to delete the other security
        # group since it is in use by an active server
        self.assertRaises(exceptions.BadRequest,
                          self.client.delete_security_group,
                          sg2['id'])

        # Shutdown the server and then verify we can destroy the
        # security groups, since no active server instance is using them
        self.servers_client.delete_server(server_id)
        self.servers_client.wait_for_server_termination(server_id)

        resp, _ = self.client.delete_security_group(sg['id'])
        self.assertEqual(202, resp.status)
        resp, _ = self.client.delete_security_group(sg2['id'])
        self.assertEqual(202, resp.status)

    @test.attr(type='smoke')
    @test.services('network')
    def test_update_security_groups(self):
        # Update security group name and description
        # Create a security group
        resp, securitygroup = self.create_security_group()
        self.assertEqual(200, resp.status)
        self.assertIn('id', securitygroup)
        securitygroup_id = securitygroup['id']
        # Update the name and description
        s_new_name = data_utils.rand_name('sg-hth-')
        s_new_des = data_utils.rand_name('description-hth-')
        resp, sg_new = \
            self.client.update_security_group(securitygroup_id,
                                              name=s_new_name,
                                              description=s_new_des)
        self.assertEqual(200, resp.status)
        # get the security group
        resp, fetched_group = \
            self.client.get_security_group(securitygroup_id)
        self.assertEqual(s_new_name, fetched_group['name'])
        self.assertEqual(s_new_des, fetched_group['description'])
