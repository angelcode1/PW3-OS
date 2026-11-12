"""Read-only Alpine APKINDEX browser candidate detection."""

def find_package(index_paths, name):
    for path in index_paths:
        if not path.is_file():
            continue
        for entry in path.read_text().split('\n\n'):
            fields = {}
            for line in entry.splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    fields[key] = value
            if fields.get('P') == name:
                return {'name': name, 'version': fields.get('V','unknown'),
                        'state':'available-not-installed'}
    return None
