class Component:
    def __init__(self, id, name, owner, status="Available"):
        self.id = id
        self.name = name
        self.owner = owner
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"],
            data["name"],
            data["owner"],
            data["status"]
        )

    def __str__(self):
        return (f"ID: {self.id}, "
                f"Name: {self.name}, "
                f"Owner: {self.owner}, "
                f"Status: {self.status}")