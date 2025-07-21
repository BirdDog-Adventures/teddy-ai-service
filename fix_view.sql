CREATE OR REPLACE VIEW BIRDDOG_DATA.CURATED.COMPREHENSIVE_PARCEL_CDL_ANALYSIS AS
SELECT 
    p.PARCEL_ID,
    p.ACRES AS PARCEL_ACRES,
    p.COUNTY_ID,
    p.STATE_CODE,
    p.ADDRESS,
    p.OWNER_NAME,
    
    -- Property characteristics
    p.USECODE,
    p.USEDESC,
    p.ZONING,
    p.ZONING_DESCRIPTION,
    p.HOMESTEAD_EXEMPTION,
    
    -- Valuation data
    p.TOTAL_VALUE,
    p.LAND_VALUE,
    p.IMPROVEMENT_VALUE,
    p.TAXAMT,
    p.SALEPRICE,
    p.SALEDATE,
    
    -- CDL Land cover analysis
    lc.land_cover_summary,
    lc.dominant_cover_type,
    lc.dominant_cover_percentage,
    lc.total_cover_types,
    lc.agricultural_percentage,
    lc.forest_percentage,
    lc.developed_percentage,
    
    -- Agricultural crop summary  
    ch.crop_summary,
    ch.dominant_crop,
    ch.total_agricultural_crops,
    
    -- Business intelligence flags
    CASE 
        WHEN lc.agricultural_percentage >= 50 THEN 'HIGH_AGRICULTURAL'
        WHEN lc.agricultural_percentage >= 20 THEN 'MIXED_AGRICULTURAL'
        ELSE 'NON_AGRICULTURAL'
    END AS AGRICULTURAL_CLASSIFICATION,
    
    CASE 
        WHEN lc.agricultural_percentage > 30 THEN 'HIGH'
        WHEN lc.agricultural_percentage > 10 THEN 'MEDIUM'
        ELSE 'LOW'
    END AS SECTION_180_POTENTIAL,
    
    -- Tax exemption validation
    CASE 
        WHEN p.HOMESTEAD_EXEMPTION IS NOT NULL AND lc.agricultural_percentage < 30 THEN 'EXEMPTION_QUESTIONABLE'
        WHEN p.HOMESTEAD_EXEMPTION IS NULL AND lc.agricultural_percentage > 70 THEN 'EXEMPTION_MISSED'
        ELSE 'EXEMPTION_APPROPRIATE'
    END AS TAX_EXEMPTION_ANALYSIS,
    
    -- Property value analysis enhanced with CDL
    CASE 
        WHEN p.TOTAL_VALUE / NULLIF(p.ACRES, 0) < 2000 AND lc.agricultural_percentage > 60 THEN 'UNDERVALUED_AGRICULTURAL'
        WHEN p.TOTAL_VALUE / NULLIF(p.ACRES, 0) > 10000 AND lc.developed_percentage < 10 THEN 'OVERVALUED_RURAL'
        ELSE 'APPROPRIATELY_VALUED'
    END AS VALUATION_FLAG,
    
    -- Investment opportunity scoring
    CASE 
        WHEN lc.agricultural_percentage > 60 AND p.TOTAL_VALUE / NULLIF(p.ACRES, 0) < 3000 THEN 'HIGH_INVESTMENT_OPPORTUNITY'
        WHEN lc.forest_percentage > 70 AND p.ACRES > 50 THEN 'TIMBER_INVESTMENT_OPPORTUNITY'
        WHEN lc.developed_percentage < 5 AND p.ACRES > 20 AND p.TOTAL_VALUE > 100000 THEN 'DEVELOPMENT_OPPORTUNITY'
        ELSE 'STANDARD_PROPERTY'
    END AS INVESTMENT_OPPORTUNITY_FLAG

FROM BIRDDOG_DATA.CURATED.PARCEL_PROFILE p

LEFT JOIN (
    SELECT 
        PARCEL_ID,
        LISTAGG(COVER_TYPE || ':' || VEGETATION_DENSITY || '%', ', ') AS land_cover_summary,
        MAX(CASE WHEN rn = 1 THEN COVER_TYPE END) AS dominant_cover_type,
        MAX(CASE WHEN rn = 1 THEN VEGETATION_DENSITY END) AS dominant_cover_percentage,
        COUNT(DISTINCT COVER_TYPE) AS total_cover_types,
        SUM(CASE WHEN COVER_CLASS = 'Agricultural' THEN VEGETATION_DENSITY ELSE 0 END) AS agricultural_percentage,
        SUM(CASE WHEN COVER_CLASS = 'Forest' THEN VEGETATION_DENSITY ELSE 0 END) AS forest_percentage,
        SUM(CASE WHEN COVER_CLASS = 'Developed' THEN VEGETATION_DENSITY ELSE 0 END) AS developed_percentage
    FROM (
        SELECT 
            PARCEL_ID,
            COVER_TYPE,
            COVER_CLASS,
            VEGETATION_DENSITY,
            ROW_NUMBER() OVER (PARTITION BY PARCEL_ID ORDER BY VEGETATION_DENSITY DESC) AS rn
        FROM BIRDDOG_DATA.CURATED.LAND_COVER 
        WHERE DATA_SOURCE LIKE '%cdl%'
    ) ranked_covers
    GROUP BY PARCEL_ID
) lc ON p.PARCEL_ID = lc.PARCEL_ID

LEFT JOIN (
    SELECT 
        PARCEL_ID,
        LISTAGG(CROP_TYPE, ', ') AS crop_summary,
        MAX(CASE WHEN rn = 1 THEN CROP_TYPE END) AS dominant_crop,
        COUNT(DISTINCT CROP_TYPE) AS total_agricultural_crops
    FROM (
        SELECT 
            PARCEL_ID,
            CROP_TYPE,
            ROTATION_SEQUENCE,
            ROW_NUMBER() OVER (PARTITION BY PARCEL_ID ORDER BY ROTATION_SEQUENCE) AS rn
        FROM BIRDDOG_DATA.CURATED.CROP_HISTORY
    ) ranked_crops
    GROUP BY PARCEL_ID
) ch ON p.PARCEL_ID = ch.PARCEL_ID;