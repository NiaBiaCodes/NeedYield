from app.services.location_service import location_service


def get_inventory(location_id: str) -> dict[str, int]:
    location = location_service.get(location_id)
    if not location:
        raise KeyError("Location not found")
    return location.inventory


def add_inventory(location_id: str, item: str, quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return location_service.mutate_inventory(location_id, item, quantity)


def reserve_inventory(location_id: str, item: str, quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return location_service.mutate_inventory(location_id, item, -quantity)


def release_inventory(location_id: str, item: str, quantity: int) -> int:
    return add_inventory(location_id, item, quantity)

