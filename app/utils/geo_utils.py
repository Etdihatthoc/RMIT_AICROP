"""
Geo-spatial utilities for epidemic detection
"""

from geopy.distance import geodesic
from typing import Tuple
import math


def haversine_distance(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float]
) -> float:
    """
    Calculate distance between two GPS coordinates in kilometers
    Uses geodesic (more accurate than haversine for most cases)

    Args:
        coord1: (latitude, longitude) tuple
        coord2: (latitude, longitude) tuple

    Returns:
        Distance in kilometers
    """
    return geodesic(coord1, coord2).km


def calculate_cluster_center(coordinates: list) -> Tuple[float, float]:
    """
    Calculate the center point of a cluster of coordinates

    Args:
        coordinates: List of (lat, lon) tuples

    Returns:
        (center_lat, center_lon) tuple
    """
    if not coordinates:
        return (0.0, 0.0)

    avg_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
    avg_lon = sum(coord[1] for coord in coordinates) / len(coordinates)

    return (avg_lat, avg_lon)


def calculate_cluster_radius(
    center: Tuple[float, float],
    coordinates: list
) -> float:
    """
    Calculate the maximum radius of a cluster from its center

    Args:
        center: (lat, lon) tuple of cluster center
        coordinates: List of (lat, lon) tuples in the cluster

    Returns:
        Maximum radius in kilometers
    """
    if not coordinates:
        return 0.0

    max_distance = 0.0
    for coord in coordinates:
        distance = haversine_distance(center, coord)
        max_distance = max(max_distance, distance)

    return max_distance


def is_within_radius(
    center: Tuple[float, float],
    point: Tuple[float, float],
    radius_km: float
) -> bool:
    """
    Check if a point is within a given radius of a center point

    Args:
        center: (lat, lon) of center
        point: (lat, lon) to check
        radius_km: Radius in kilometers

    Returns:
        True if point is within radius
    """
    distance = haversine_distance(center, point)
    return distance <= radius_km
