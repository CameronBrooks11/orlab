def _get_private_field(obj, field_name):
    field = obj.getClass().getDeclaredField(field_name)
    field.setAccessible(True)
    ret = field.get(obj)
    field.setAccessible(False)
    return ret
