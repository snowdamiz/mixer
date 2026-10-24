"""Raw PG17 capture contract, checked before any lossy normalization.

This validates transport shape and domains only. It neither selects expected
state nor grants admission: the unchanged exact comparator still decides that.
OID associations are validated for presence, not numeric equality across rows;
their resolved semantic identities remain the portable comparison contract.
"""
import re

UINT32_MAX = 4294967295
NAME_BYTES = 63  # frozen PG17 pg_config_manual.h: NAMEDATALEN - 1


def reject(where):
    raise ValueError('malformed raw value: ' + where)


def keys(value, fields, where):
    if type(value) is not dict or set(value) != set(fields):
        reject(where + ' keys')


def text(value, where, empty=False, identifier=False):
    if type(value) is not str or (not empty and not value) or '\x00' in value:
        reject(where + ' text')
    try:
        encoded = value.encode('utf-8', errors='strict')
    except UnicodeError:
        reject(where + ' UTF8')
    if identifier and len(encoded) > NAME_BYTES:
        reject(where + ' identifier bytes')


def integer(value, lo, hi, where):
    if type(value) is not int or not lo <= value <= hi:
        reject(where + ' integer range')


# Complete field domains from the independent review. No SQL query changes.
GROUPS = {
    'relations': {
        'oid':'positive_oid', 'identity':'text', 'kind':'relation_kind',
        'persistence':'persistence', 'replica_identity':'replica_identity'},
    'constraints': {
        'oid':'positive_oid', 'identity':'text', 'relation':'text',
        'type':'constraint_type', 'validated':'bool', 'deferrable':'bool',
        'initially_deferred':'bool', 'no_inherit':'bool', 'local':'bool',
        'inheritance_count':'int16', 'parent_oid':'optional_oid',
        'parent_identity':'nullable_text', 'definition':'text'},
    'indexes': {
        'oid':'positive_oid', 'identity':'text', 'relation':'text',
        'valid':'bool', 'ready':'bool', 'live':'bool', 'immediate':'bool',
        'unique':'bool', 'primary':'bool', 'exclusion':'bool',
        'nulls_not_distinct':'bool', 'definition':'text'},
    'triggers': {
        'oid':'positive_oid', 'name':'identifier', 'relation_oid':'positive_oid',
        'relation':'text', 'function_oid':'positive_oid', 'function_identity':'text',
        'enabled':'trigger_enable_mode', 'internal':'bool', 'event_timing_bits':'trigger_bits',
        'deferrable':'bool', 'initially_deferred':'bool', 'constraint_oid':'optional_oid',
        'constraint_identity':'nullable_text', 'referenced_relation_oid':'optional_oid',
        'referenced_relation':'nullable_text', 'constraint_index_oid':'optional_oid',
        'constraint_index':'nullable_text', 'parent_oid':'optional_oid',
        'parent_identity':'nullable_parent', 'argument_count':'int16',
        'argument_hex':'hex', 'columns':'int2vector', 'when':'nullable_text',
        'old_table':'nullable_identifier', 'new_table':'nullable_identifier', 'definition':'text'},
    'parameter_acl': {
        'oid':'positive_oid', 'parameter':'text', 'acl':'nullable_text',
        'entries':'nullable_acl_entries'},
    'parameter_effective': {
        'subject':'text', 'parameter':'text', 'context':'nullable_text',
        'registered':'bool', 'selected_set':'bool', 'set':'bool', 'alter_system':'bool'},
    'parameter_public': {
        'parameter':'text', 'context':'nullable_text', 'registered':'bool',
        'selected_set':'bool', 'set':'bool', 'alter_system':'bool'},
    'role_config': {'role':'text', 'config':'nullable_config'},
    'startup_defaults': {
        'database_oid':'optional_oid', 'database':'nullable_text',
        'role_oid':'optional_oid', 'role':'nullable_text', 'config':'nullable_config'},
}
SESSION_FIELDS = 'session_user current_user role database session_replication_role row_security default_transaction_isolation transaction_isolation transaction_read_only'.split()


def domain(value, name, where):
    if name.startswith('nullable_'):
        if value is None:
            return
        name = name[len('nullable_'):]
    if name == 'bool':
        if type(value) is not bool:
            reject(where + ' boolean')
    elif name in ('text', 'identifier', 'empty_text'):
        text(value, where, empty=name == 'empty_text', identifier=name == 'identifier')
    elif name in ('positive_oid', 'optional_oid', 'int16'):
        integer(value, 1 if name == 'positive_oid' else 0,
                32767 if name == 'int16' else UINT32_MAX, where)
    elif name in ('relation_kind', 'constraint_type', 'persistence', 'replica_identity', 'trigger_enable_mode'):
        allowed = {'relation_kind':'ripvImSftc', 'constraint_type':'cfnpxut',
                   'persistence':'put', 'replica_identity':'dnfi', 'trigger_enable_mode':'ODRA'}[name]
        if type(value) is not str or len(value) != 1 or value not in allowed:
            reject(where + ' enum')
    elif name == 'trigger_bits':
        integer(value, 0, 32767, where)
        # PG17 pg_trigger.h defines row=1, timing=2|64, events=4|8|16|32.
        if value & ~127 or not value & 60 or value & 66 == 66:
            reject(where + ' event/timing bits')
        if value & 1 and value & 32:  # TRUNCATE is statement-only.
            reject(where + ' row TRUNCATE')
        if value & 64 and (not value & 1 or value & 32):
            reject(where + ' INSTEAD level/event')
    elif name == 'hex':
        text(value, where, empty=True)
        if len(value) % 2 or re.fullmatch('[0-9a-f]*', value) is None:
            reject(where + ' even lowercase hex')
    elif name == 'int2vector':
        text(value, where, empty=True)
        if value:
            if re.fullmatch('[1-9][0-9]*( [1-9][0-9]*)*', value) is None:
                reject(where + ' attribute vector')
            for item in value.split(' '):
                integer(int(item), 1, 32767, where)
    elif name == 'parent':
        keys(value, ['relation', 'name'], where)
        domain(value['relation'], 'text', where + '.relation')
        domain(value['name'], 'identifier', where + '.name')
    elif name == 'acl_entries':
        if type(value) is not list:
            reject(where + ' ACL array')
        for i, entry in enumerate(value):
            at = where + '[' + str(i) + ']'
            keys(entry, ['grantor', 'grantee', 'privilege', 'grantable'], at)
            domain(entry['grantor'], 'text', at + '.grantor')
            domain(entry['grantee'], 'text', at + '.grantee')
            domain(entry['grantable'], 'bool', at + '.grantable')
            if type(entry['privilege']) is not str or entry['privilege'] not in ('SET', 'ALTER SYSTEM'):
                reject(at + '.privilege')
    elif name == 'config':
        if type(value) is not list:
            reject(where + ' config array')
        for i, setting in enumerate(value):
            at = where + '[' + str(i) + ']'
            text(setting, at)
            # Empty setting values are legitimate (e.g. application_name=).
            if '=' not in setting or not setting.split('=', 1)[0]:
                reject(at + ' name=value')
    else:
        raise AssertionError('unknown validator domain: ' + name)


def association(row, oid_field, identity, where):
    if (row[oid_field] == 0) != (row[identity] is None):
        reject(where + ' unresolved ' + identity)


def validate_raw(raw):
    keys(raw, ['legacy', 'enforcement', 'fresh_session'], 'root')
    validate_legacy(raw['legacy'])
    keys(raw['fresh_session'], SESSION_FIELDS, 'fresh_session')
    for field in SESSION_FIELDS:
        domain(raw['fresh_session'][field], 'text', 'fresh_session.' + field)
    enforcement = raw['enforcement']
    keys(enforcement, GROUPS, 'enforcement')
    for group, fields in GROUPS.items():
        rows = enforcement[group]
        if type(rows) is not list:
            reject(group + ' array')
        seen_oids = set()
        seen_trigger_names = set()
        for i, row in enumerate(rows):
            at = group + '[' + str(i) + ']'
            keys(row, fields, at)
            for field, name in fields.items():
                domain(row[field], name, at + '.' + field)
            if 'oid' in row:
                if row['oid'] in seen_oids:
                    reject(at + ' duplicate OID')
                seen_oids.add(row['oid'])
            if group in ('constraints', 'triggers'):
                association(row, 'parent_oid', 'parent_identity', at)
            if group == 'triggers':
                key = (row['relation_oid'], row['name'])
                if key in seen_trigger_names:
                    reject(at + ' duplicate relation/name')
                seen_trigger_names.add(key)
                for oid_field, identity in [('constraint_oid', 'constraint_identity'),
                                            ('referenced_relation_oid', 'referenced_relation'),
                                            ('constraint_index_oid', 'constraint_index')]:
                    association(row, oid_field, identity, at)
                if row['internal'] and row['constraint_identity'] is None:
                    reject(at + ' unselected internal trigger without constraint')
                arguments = bytes.fromhex(row['argument_hex'])
                if arguments.count(b'\x00') != row['argument_count'] or (arguments and not arguments.endswith(b'\x00')):
                    reject(at + ' argument count/terminator')
            if group == 'startup_defaults':
                for field in ('database', 'role'):
                    if row[field] is None or (row[field + '_oid'] == 0 and row[field] != '*'):
                        reject(at + ' wildcard association ' + field)
            if group in ('parameter_effective', 'parameter_public'):
                if row['registered'] != (row['context'] is not None):
                    reject(at + ' registered context')
                selected = not row['registered'] or row['context'] in ('superuser', 'superuser-backend')
                if row['selected_set'] != selected:
                    reject(at + ' selected parameter context')


# Legacy SQL is unchanged and retains every value. These descriptors enforce
# its complete raw nested shape; exact selected equality remains in validate().
def objects(value, fields, where, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not list:
        reject(where + ' array')
    for i, row in enumerate(value):
        object_fields(row, fields, where + '[' + str(i) + ']')


def object_fields(value, fields, where):
    keys(value, fields, where)
    for field, descriptor in fields.items():
        at = where + '.' + field
        if isinstance(descriptor, tuple):
            kind, item = descriptor
            if kind == 'object':
                object_fields(value[field], item, at)
            elif kind in ('objects', 'nullable_objects'):
                objects(value[field], item, at, nullable=kind == 'nullable_objects')
            elif kind in ('strings', 'nullable_strings'):
                if value[field] is None and kind == 'nullable_strings':
                    continue
                if type(value[field]) is not list:
                    reject(at + ' array')
                for i, entry in enumerate(value[field]):
                    domain(entry, item, at + '[' + str(i) + ']')
            else:
                raise AssertionError(kind)
        else:
            domain(value[field], descriptor, at)


def validate_legacy(value):
    column = {'name':'identifier', 'type':'text', 'notnull':'bool', 'acl':'empty_text', 'collation':'nullable_text'}
    constraint = {'name':'identifier', 'definition':'text'}
    fields = {'name':'identifier', 'type':'text'}
    table = {'name':'identifier', 'owner':'identifier', 'rls':'bool', 'force':'bool', 'acl':'empty_text',
             'columns':('nullable_objects', column), 'constraints':('nullable_objects', constraint),
             'indexes':('nullable_strings', 'text'), 'triggers':('nullable_strings', 'text')}
    function = {'identity':'text', 'owner':'identifier', 'security_definer':'bool',
                'volatility':'text', 'parallel':'text', 'leakproof':'bool', 'language':'identifier',
                'config':'nullable_config', 'acl':'empty_text', 'definition':'text',
                'definition_sha256':'text', 'public_execute':'bool', 'runtime_execute':'bool', 'writer_execute':'bool'}
    legacy = {
        'server_version':'text',
        'schemas':('nullable_objects', {'name':'identifier', 'owner':'identifier', 'acl':'empty_text'}),
        'roles':('nullable_objects', {'name':'identifier', 'login':'bool', 'super':'bool', 'bypass':'bool',
                                    'createdb':'bool', 'createrole':'bool', 'replication':'bool', 'inherit':'bool'}),
        'memberships':('objects', {'role':'identifier', 'member':'identifier', 'admin':'bool', 'inherit':'bool', 'set':'bool'}),
        'database':('object', {'name':'identifier', 'owner':'identifier', 'acl':'empty_text'}),
        'tables':('nullable_objects', table),
        'types':('nullable_objects', {'name':'identifier', 'owner':'identifier', 'acl':'empty_text', 'fields':('nullable_objects', fields)}),
        'functions':('nullable_objects', function),
        'policies':('nullable_objects', {'table':'identifier', 'name':'identifier', 'permissive':'text',
                                        'roles':('strings', 'identifier'), 'command':'text', 'using':'nullable_text', 'check':'nullable_text'}),
        'default_acl':('objects', {'owner':'identifier', 'schema':'empty_text', 'type':'text', 'acl':'text'}),
        'runtime_owned_objects':('strings', 'text'),
        'runtime_creatable_schemas':('strings', 'identifier'),
        'runtime_capabilities':('object', {'database_create':'bool', 'database_temp':'bool', 'public_create':'bool',
                                          'authz_create':'bool', 'reachable':('strings', 'identifier')})}
    object_fields(value, legacy, 'legacy')
