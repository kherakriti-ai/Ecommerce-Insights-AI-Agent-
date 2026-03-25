CREATE OR REPLACE SEMANTIC VIEW ECOMMERCE.RETAIL.ECOMMERCE_SEMANTIC_VIEW
  TABLES (
    customer_behavior AS ECOMMERCE.RETAIL.CUSTOMER_BEHAVIOR
      PRIMARY KEY (ORDER_ID)
  )
  FACTS (
    customer_behavior.unit_price AS UNIT_PRICE,
    customer_behavior.quantity AS QUANTITY,
    customer_behavior.discount_amount AS DISCOUNT_AMOUNT,
    customer_behavior.total_amount AS TOTAL_AMOUNT,
    customer_behavior.session_duration_minutes AS SESSION_DURATION_MINUTES,
    customer_behavior.pages_viewed AS PAGES_VIEWED,
    customer_behavior.delivery_time_days AS DELIVERY_TIME_DAYS,
    customer_behavior.customer_rating AS CUSTOMER_RATING
  )
  DIMENSIONS (
    customer_behavior.order_id AS ORDER_ID,
    customer_behavior.customer_id AS CUSTOMER_ID,
    customer_behavior.order_date AS DATE,
    customer_behavior.age AS AGE,
    customer_behavior.gender AS GENDER,
    customer_behavior.city AS CITY,
    customer_behavior.product_category AS PRODUCT_CATEGORY,
    customer_behavior.payment_method AS PAYMENT_METHOD,
    customer_behavior.device_type AS DEVICE_TYPE,
    customer_behavior.is_returning_customer AS IS_RETURNING_CUSTOMER
  )
  METRICS (
    customer_behavior.total_revenue AS SUM(customer_behavior.TOTAL_AMOUNT),
    customer_behavior.total_orders AS COUNT(customer_behavior.ORDER_ID),
    customer_behavior.avg_order_value AS AVG(customer_behavior.TOTAL_AMOUNT),
    customer_behavior.avg_session_duration AS AVG(customer_behavior.SESSION_DURATION_MINUTES),
    customer_behavior.avg_pages_viewed AS AVG(customer_behavior.PAGES_VIEWED),
    customer_behavior.avg_delivery_time AS AVG(customer_behavior.DELIVERY_TIME_DAYS),
    customer_behavior.avg_rating AS AVG(customer_behavior.CUSTOMER_RATING),
    customer_behavior.revenue_per_customer AS
      SUM(customer_behavior.TOTAL_AMOUNT) / COUNT(DISTINCT customer_behavior.CUSTOMER_ID),
    customer_behavior.discount_rate AS
      SUM(customer_behavior.DISCOUNT_AMOUNT) /
      NULLIF(SUM(customer_behavior.UNIT_PRICE * customer_behavior.QUANTITY), 0),

    customer_behavior.engagement_score AS
      AVG(customer_behavior.SESSION_DURATION_MINUTES * 0.6 + customer_behavior.PAGES_VIEWED * 0.4),

    customer_behavior.conversion_proxy AS
      SUM(customer_behavior.TOTAL_AMOUNT) /
      NULLIF(SUM(customer_behavior.PAGES_VIEWED), 0)
  )
  COMMENT = 'Semantic view for ecommerce sales, customer behavior, and operational performance';
