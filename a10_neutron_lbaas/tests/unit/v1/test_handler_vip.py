# Copyright 2014, Doug Wiegley (dougwig), A10 Networks
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

import mock
import test_base

from a10_neutron_lbaas import a10_common
import a10_neutron_lbaas.a10_exceptions as a10_ex


class TestVIP(test_base.UnitTestBase):

    def fake_vip(self, pers=None):
        h = {
            'tenant_id': 'ten1',
            'id': 'id1',
            'protocol': 'HTTP',
            'admin_state_up': True,
            'address': '1.1.1.1',
            'protocol_port': '80',
            'pool_id': 'pool1',
        }
        if pers:
            h['session_persistence'] = {'type': pers}
        return h.copy()

    def test_create(self):
        self.a.vip.create(None, self.fake_vip())
        s = str(self.a.last_client.mock_calls)
        self.assertTrue('virtual_server.create' in s)
        self.assertTrue('1.1.1.1' in s)
        self.assertTrue('vport.create' in s)
        self.assertTrue('id1' in s)
        self.assertTrue('UP' in s)
        self.a.openstack_driver.plugin.get_pool.assert_called_with(
            None, 'pool1')
        self.assertTrue('HTTP' in s)

    def test_create_pers(self):
        self.a.vip.create(None, self.fake_vip('HTTP_COOKIE'))
        s = str(self.a.last_client.mock_calls)
        self.assertTrue("c_pers_name='id1'" in s)

    def test_create_unsupported(self):
        try:
            self.a.vip.create(None, self.fake_vip('APP_COOKIE'))
        except a10_ex.UnsupportedFeature:
            pass

    def test_create_autosnat_false_v21(self):
        self._test_create_autosnat("2.1", False)

    def test_create_autosnat_true_v21(self):
        self._test_create_autosnat("2.1", True)

    def test_create_autosnat_true_v30(self):
        self._test_create_autosnat("3.0", True)

    def test_create_autosnat_false_v30(self):
        self._test_create_autosnat("3.0", False)

    def _test_create_autosnat(self, api_ver=None, autosnat=None):
        auto_expected = None
        key = None
        transform = None

        """
        Due to how the config is pulled in, we can't override the config
        version here and just expect it to work.
        """
        for k, v in self.a.config.devices.items():
            v['api_version'] = api_ver
            v['autosnat'] = autosnat

        expected_tuple = a10_common.auto_dictionary.get(api_ver, None)

        vip = self.fake_vip()
        if expected_tuple is not None:
            key = expected_tuple[0]
            transform = expected_tuple[1]

        if autosnat and key is not None and transform is not None:
            auto_format = "'{0}': {1}"
            auto_expected = auto_format.format(key, transform(autosnat))

        self.a.vip.create(None, vip)
        s = str(self.a.last_client.mock_calls)
        self.assertTrue('virtual_server.create' in s)

        if auto_expected is not None:
            self.assertTrue(auto_expected in s)

    def test_create_default_vrid_none_v21(self):
        self._test_create_default_vrid("2.1", None)

    def test_create_default_vrid_set_v21(self):
        self._test_create_default_vrid("2.1", 7)

    def test_create_default_vrid_none_v30(self):
        self._test_create_default_vrid("3.0", None)

    def test_create_default_vrid_set_v30(self):
        self._test_create_default_vrid("3.0", 7)

    def _test_create_default_vrid(self, api_ver=None, default_vrid=None):

        """
        Due to how the config is pulled in, we override the config
        for all of the devices.
        """

        for k, v in self.a.config.devices.items():
            v['api_version'] = api_ver
            v['default_virtual_server_vrid'] = default_vrid

        vip = self.fake_vip()
        self.a.vip.create(None, vip)

        create = self.a.last_client.slb.virtual_server.create
        create.assert_has_calls([mock.ANY])
        calls = create.call_args_list

        if default_vrid is not None:
            foundVrid = any(
                x.get('axapi_args', {}).get('virtual_server', {}).get('vrid', {}) is default_vrid
                for (_, x) in calls)
            self.assertTrue(
                foundVrid,
                'Expected to find vrid {0} in {1}'.format(default_vrid, str(calls)))
        if default_vrid is None:
            foundVrid = any(
                'vrid' in x.get('axapi_args', {}).get('virtual_server', {})
                for (_, x) in calls)
            self.assertFalse(
                foundVrid,
                'Expected to find no vrid in {0}'.format(str(calls)))

    def _test_create_ipinip(self, ip_in_ip=False):
        for k, v in self.a.config.devices.items():
            v['ipinip'] = ip_in_ip

        vip = self.fake_vip()
        self.a.vip.create(None, vip)
        s = str(self.a.last_client.mock_calls)
        self.assertEqual(ip_in_ip, "ipinip" in s)

    def test_create_ip_in_ip_positive(self):
        self._test_create_ipinip(True)

    def test_create_ip_in_ip_negative(self):
        self._test_create_ipinip()

    def test_update(self):
        self.a.vip.update(None, self.fake_vip(), self.fake_vip())
        self.print_mocks()
        s = str(self.a.last_client.mock_calls)
        self.assertTrue('vport.update' in s)
        self.assertTrue('id1' in s)
        self.assertTrue('UP' in s)
        self.a.openstack_driver.plugin.get_pool.assert_called_with(
            None, 'pool1')
        self.assertTrue('HTTP' in s)

    def test_delete(self):
        self.a.vip.delete(None, self.fake_vip())
        self.a.last_client.slb.virtual_server.delete.assert_called_with('id1')

    def test_delete_pers(self):
        self.a.vip.delete(None, self.fake_vip('SOURCE_IP'))
        self.a.last_client.slb.virtual_server.delete.assert_called_with('id1')
        z = self.a.last_client.slb.template.src_ip_persistence.delete
        z.assert_called_with('id1')
