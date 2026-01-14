"""
UC-02: Epidemic Detection Service
DBSCAN clustering for disease outbreak detection
"""

from sklearn.cluster import DBSCAN
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from app.database.models import Diagnosis, EpidemicAlert
from app.utils.geo_utils import (
    calculate_cluster_center,
    calculate_cluster_radius,
    haversine_distance
)
from app.config import settings

logger = logging.getLogger(__name__)


def check_epidemic_clusters(
    diagnosis: Diagnosis,
    db: Session
) -> List[EpidemicAlert]:
    """
    Check if new diagnosis creates/updates epidemic clusters
    Called after each diagnosis is saved

    Args:
        diagnosis: Newly created diagnosis
        db: Database session

    Returns:
        List of newly created or updated epidemic alerts
    """
    if not diagnosis.disease_detected:
        logger.info("No disease detected, skipping epidemic check")
        return []

    if not diagnosis.latitude or not diagnosis.longitude:
        logger.info("No GPS coordinates, skipping epidemic check")
        return []

    if not diagnosis.province:
        logger.info("No province specified, skipping epidemic check")
        return []

    # Get recent diagnoses for the same disease in the same province
    lookback_date = datetime.utcnow() - timedelta(days=settings.epidemic_lookback_days)

    recent_cases = db.query(Diagnosis).filter(
        and_(
            Diagnosis.disease_detected == diagnosis.disease_detected,
            Diagnosis.province == diagnosis.province,
            Diagnosis.created_at >= lookback_date,
            Diagnosis.confidence >= 0.5,  # Only consider confident diagnoses
            Diagnosis.latitude.isnot(None),
            Diagnosis.longitude.isnot(None)
        )
    ).all()

    logger.info(
        f"Found {len(recent_cases)} recent cases of '{diagnosis.disease_detected}' "
        f"in {diagnosis.province} (last {settings.epidemic_lookback_days} days)"
    )

    if len(recent_cases) < settings.dbscan_min_samples:
        logger.info(f"Not enough cases for clustering (need {settings.dbscan_min_samples})")
        return []

    # Run DBSCAN clustering
    clusters = run_dbscan_clustering(recent_cases, db)

    logger.info(f"Detected {len(clusters)} epidemic clusters")

    return clusters


def run_dbscan_clustering(
    diagnoses: List[Diagnosis],
    db: Session
) -> List[EpidemicAlert]:
    """
    Run DBSCAN clustering on diagnoses to detect epidemic hotspots

    Args:
        diagnoses: List of diagnoses with GPS coordinates
        db: Database session

    Returns:
        List of epidemic alerts (newly created or updated)
    """
    if len(diagnoses) < settings.dbscan_min_samples:
        return []

    # Extract coordinates
    coordinates = np.array([
        [d.latitude, d.longitude] for d in diagnoses
    ])

    # Run DBSCAN
    # eps is in degrees, ~0.05 degrees ≈ 5km at equator
    clustering = DBSCAN(
        eps=settings.dbscan_eps,
        min_samples=settings.dbscan_min_samples,
        metric='euclidean'
    ).fit(coordinates)

    labels = clustering.labels_

    # Process each cluster
    created_alerts = []

    for label in set(labels):
        if label == -1:  # Noise points
            continue

        # Get diagnoses in this cluster
        cluster_indices = np.where(labels == label)[0]
        cluster_diagnoses = [diagnoses[i] for i in cluster_indices]
        cluster_coords = coordinates[cluster_indices]

        # Calculate cluster metrics
        center_lat, center_lon = calculate_cluster_center(
            [(coord[0], coord[1]) for coord in cluster_coords]
        )
        radius_km = calculate_cluster_radius(
            (center_lat, center_lon),
            [(coord[0], coord[1]) for coord in cluster_coords]
        )

        case_count = len(cluster_diagnoses)
        disease_name = cluster_diagnoses[0].disease_detected
        province = cluster_diagnoses[0].province

        # Determine severity based on case count
        if case_count >= 15:
            severity = "high"
        elif case_count >= 10:
            severity = "medium"
        else:
            severity = "low"

        # Check if alert already exists for this cluster
        # (Within 10km of center, same disease, same province, active)
        existing_alert = db.query(EpidemicAlert).filter(
            and_(
                EpidemicAlert.disease_name == disease_name,
                EpidemicAlert.province == province,
                EpidemicAlert.alert_status == "active"
            )
        ).first()

        if existing_alert:
            # Update existing alert
            distance_from_existing = haversine_distance(
                (existing_alert.center_lat, existing_alert.center_lon),
                (center_lat, center_lon)
            )

            if distance_from_existing <= 10:  # Within 10km, consider same cluster
                logger.info(f"Updating existing alert {existing_alert.id}")
                existing_alert.case_count = case_count
                existing_alert.radius_km = radius_km
                existing_alert.center_lat = center_lat
                existing_alert.center_lon = center_lon
                existing_alert.severity = severity
                existing_alert.alert_message = generate_alert_message(
                    disease_name, province, case_count, radius_km
                )
                db.commit()
                created_alerts.append(existing_alert)
                continue

        # Create new alert
        logger.info(f"Creating new epidemic alert: {disease_name} in {province}")

        alert = EpidemicAlert(
            disease_name=disease_name,
            province=province,
            district=cluster_diagnoses[0].district,
            case_count=case_count,
            radius_km=round(radius_km, 2),
            center_lat=center_lat,
            center_lon=center_lon,
            severity=severity,
            alert_status="active",
            alert_message=generate_alert_message(
                disease_name, province, case_count, radius_km
            )
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        created_alerts.append(alert)
        logger.info(f"✓ Epidemic alert created: ID {alert.id}")

    return created_alerts


def generate_alert_message(
    disease_name: str,
    province: str,
    case_count: int,
    radius_km: float
) -> str:
    """
    Generate human-readable alert message

    Args:
        disease_name: Name of disease
        province: Province name
        case_count: Number of cases
        radius_km: Cluster radius

    Returns:
        Alert message string
    """
    return (
        f"⚠️ CẢNH BÁO DỊCh BỆNH: Phát hiện ổ dịch {disease_name} tại {province}. "
        f"{case_count} trường hợp trong bán kính {radius_km:.1f}km. "
        f"Nông dân trong khu vực cần chú ý phòng ngừa."
    )


def get_active_alerts(
    db: Session,
    province: Optional[str] = None,
    district: Optional[str] = None,
    disease: Optional[str] = None
) -> List[EpidemicAlert]:
    """
    Get active epidemic alerts with optional filters

    Args:
        db: Database session
        province: Filter by province (optional)
        district: Filter by district (optional)
        disease: Filter by disease name (optional)

    Returns:
        List of active epidemic alerts
    """
    query = db.query(EpidemicAlert).filter(
        EpidemicAlert.alert_status == "active"
    )

    if province:
        query = query.filter(EpidemicAlert.province == province)

    if district:
        query = query.filter(EpidemicAlert.district == district)

    if disease:
        query = query.filter(EpidemicAlert.disease_name == disease)

    alerts = query.order_by(EpidemicAlert.created_at.desc()).all()

    return alerts


def get_heatmap_data(
    db: Session,
    disease: Optional[str] = None,
    province: Optional[str] = None,
    days: int = 30
) -> List[Dict]:
    """
    Get diagnosis data for heatmap visualization

    Args:
        db: Database session
        disease: Filter by disease (optional)
        province: Filter by province (optional)
        days: Number of days to look back (default: 30)

    Returns:
        List of data points with coordinates and metadata
    """
    lookback_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(Diagnosis).filter(
        and_(
            Diagnosis.created_at >= lookback_date,
            Diagnosis.latitude.isnot(None),
            Diagnosis.longitude.isnot(None),
            Diagnosis.confidence >= 0.5  # Only confident diagnoses
        )
    )

    if disease:
        query = query.filter(Diagnosis.disease_detected == disease)

    if province:
        query = query.filter(Diagnosis.province == province)

    diagnoses = query.all()

    # Convert to heatmap data points
    data_points = []
    for diag in diagnoses:
        data_points.append({
            "latitude": diag.latitude,
            "longitude": diag.longitude,
            "case_count": 1,  # Each diagnosis is 1 case
            "severity": diag.severity or "unknown",
            "date": diag.created_at.strftime("%Y-%m-%d"),
            "disease": diag.disease_detected
        })

    return data_points
