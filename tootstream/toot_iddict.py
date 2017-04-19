
class TootIdDict:
    """Represents a mapping of local (tootstream) ID's to global
    (mastodon) IDs."""
    def __init__(self):
        self._map = []

    def to_local(self, global_id):
        """Returns the local ID for a global ID or None if ID is invalid."""
        try:
            global_id = int(global_id) # In case a string gets passed
        except:
            return None
        try:
            return self._map.index(global_id)
        except ValueError:
            self._map.append(global_id)
            return len(self._map) - 1

    def to_global(self, local_id):
        """Returns the global ID for a local ID, or None if ID is invalid."""
        try:
            local_id = int(local_id)
            return self._map[local_id]
        except:
            return None

