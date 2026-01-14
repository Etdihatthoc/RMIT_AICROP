"""
UC-02: Epidemic Alert API Routes
Geo-spatial epidemic detection and alerting
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database.connection import get_db
from app.models.response_models import (
    EpidemicAlertsResponse,
    EpidemicAlertResponse,
    EpidemicMapResponse,
    HeatmapDataPoint,
    ErrorResponse
)
from app.services.epidemic_service import (
    get_active_alerts,
    get_heatmap_data
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/epidemic/alerts",
    response_model=EpidemicAlertsResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_epidemic_alerts(
    province: Optional[str] = Query(None, description="Filter by province"),
    district: Optional[str] = Query(None, description="Filter by district"),
    disease: Optional[str] = Query(None, description="Filter by disease name"),
    db: Session = Depends(get_db)
):
    """
    **UC-02: Get Active Epidemic Alerts**

    Retrieve active epidemic alerts with optional filters.

    Epidemic alerts are automatically generated when DBSCAN clustering detects
    disease outbreaks (5+ cases within 5km radius in the last 7 days).

    **Query Parameters:**
    - **province**: Filter alerts by province (e.g., "An Giang")
    - **district**: Filter alerts by district
    - **disease**: Filter alerts by disease name (e.g., "Đạo ôn lúa")

    **Returns:**
    - List of active epidemic alerts with:
      - Disease name and location
      - Number of cases in cluster
      - Cluster radius (km)
      - Severity level (low/medium/high)
      - Alert message for authorities
      - GPS coordinates of cluster center

    **Use Cases:**
    - Display alerts on mobile app
    - Notify farmers in affected areas
    - Alert agricultural authorities
    - Show epidemic zones on map
    """
    try:
        logger.info(f"Getting epidemic alerts - Province: {province}, Disease: {disease}")

        alerts = get_active_alerts(
            db=db,
            province=province,
            district=district,
            disease=disease
        )

        # Convert to response model
        alert_responses = [
            EpidemicAlertResponse(
                alert_id=alert.id,
                disease_name=alert.disease_name,
                province=alert.province,
                district=alert.district,
                case_count=alert.case_count,
                radius_km=alert.radius_km,
                severity=alert.severity,
                alert_message=alert.alert_message,
                center_lat=alert.center_lat,
                center_lon=alert.center_lon,
                alert_status=alert.alert_status,
                created_at=alert.created_at
            )
            for alert in alerts
        ]

        logger.info(f"Found {len(alert_responses)} active alerts")

        return EpidemicAlertsResponse(alerts=alert_responses)

    except Exception as e:
        logger.error(f"Error retrieving epidemic alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve epidemic alerts: {str(e)}"
        )


@router.get(
    "/epidemic/map",
    response_model=EpidemicMapResponse,
    responses={500: {"model": ErrorResponse}}
)
async def get_epidemic_map(
    disease: Optional[str] = Query(None, description="Filter by disease name"),
    province: Optional[str] = Query(None, description="Filter by province"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back (default: 30)"),
    db: Session = Depends(get_db)
):
    """
    **UC-02: Get Epidemic Heatmap Data**

    Retrieve diagnosis data for heatmap visualization on mobile app.

    Returns GPS coordinates of all recent diagnoses (with confidence >= 50%)
    for creating heatmap overlays showing disease distribution.

    **Query Parameters:**
    - **disease**: Filter by specific disease (optional)
    - **province**: Filter by province (optional)
    - **days**: Number of days to look back (1-365, default: 30)

    **Returns:**
    - Total case count
    - List of data points with:
      - GPS coordinates (latitude, longitude)
      - Severity level
      - Date of diagnosis
      - Disease name

    **Use Cases:**
    - Display disease distribution heatmap on map
    - Identify high-risk areas
    - Track disease spread over time
    - Visualize epidemic patterns

    **Android Integration:**
    ```kotlin
    // Use with Google Maps Heatmap Layer
    val heatmapData = response.data_points.map { point ->
        LatLng(point.latitude, point.longitude)
    }
    heatmapLayer.setData(heatmapData)
    ```
    """
    try:
        logger.info(f"Getting heatmap data - Disease: {disease}, Province: {province}, Days: {days}")

        data_points = get_heatmap_data(
            db=db,
            disease=disease,
            province=province,
            days=days
        )

        # Convert to response model
        heatmap_points = [
            HeatmapDataPoint(
                latitude=point["latitude"],
                longitude=point["longitude"],
                case_count=point["case_count"],
                severity=point["severity"],
                date=point["date"]
            )
            for point in data_points
        ]

        logger.info(f"Found {len(heatmap_points)} data points for heatmap")

        return EpidemicMapResponse(
            disease=disease,
            province=province,
            total_cases=len(heatmap_points),
            data_points=heatmap_points
        )

    except Exception as e:
        logger.error(f"Error generating heatmap data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate heatmap data: {str(e)}"
        )


@router.get(
    "/epidemic/stats",
    responses={500: {"model": ErrorResponse}}
)
async def get_epidemic_stats(
    province: Optional[str] = Query(None, description="Filter by province"),
    db: Session = Depends(get_db)
):
    """
    **Get Epidemic Statistics**

    Summary statistics about epidemic alerts and disease distribution.

    **Returns:**
    - Total active alerts
    - Alerts by severity level
    - Most common diseases
    - Affected provinces
    """
    try:
        from sqlalchemy import func
        from app.database.models import EpidemicAlert

        # Get all active alerts
        query = db.query(EpidemicAlert).filter(
            EpidemicAlert.alert_status == "active"
        )

        if province:
            query = query.filter(EpidemicAlert.province == province)

        alerts = query.all()

        # Calculate statistics
        total_alerts = len(alerts)

        severity_counts = {
            "high": sum(1 for a in alerts if a.severity == "high"),
            "medium": sum(1 for a in alerts if a.severity == "medium"),
            "low": sum(1 for a in alerts if a.severity == "low")
        }

        # Most common diseases
        disease_counts = {}
        for alert in alerts:
            disease_counts[alert.disease_name] = disease_counts.get(alert.disease_name, 0) + 1

        # Sort by count
        top_diseases = sorted(
            disease_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5

        # Affected provinces
        affected_provinces = list(set(a.province for a in alerts))

        return {
            "total_active_alerts": total_alerts,
            "severity_breakdown": severity_counts,
            "top_diseases": [
                {"disease": disease, "alert_count": count}
                for disease, count in top_diseases
            ],
            "affected_provinces": affected_provinces,
            "total_cases": sum(a.case_count for a in alerts)
        }

    except Exception as e:
        logger.error(f"Error getting epidemic stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get epidemic statistics: {str(e)}"
        )
