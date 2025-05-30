-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: 140.131.114.242    Database: 114-205
-- ------------------------------------------------------
-- Server version	8.0.42-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Chef`
--

DROP TABLE IF EXISTS `Chef`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Chef` (
  `id` varchar(10) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `phone` varchar(15) NOT NULL,
  `service_areas` json DEFAULT NULL,
  `certificate_path` varchar(255) DEFAULT NULL,
  `specialties` json DEFAULT NULL,
  `kitchen_address` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email_UNIQUE` (`email`),
  UNIQUE KEY `phone_UNIQUE` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Chef`
--

LOCK TABLES `Chef` WRITE;
/*!40000 ALTER TABLE `Chef` DISABLE KEYS */;
INSERT INTO `Chef` VALUES ('2001','郭宗翰','11336014@ntub.edu.tw','aa0937404883','0937404883','[\"台北市\"]','uploads/2001_碧海山色.png','[\"中式料理\"]','100台北市中正區濟南路一段321號','2025-04-08 08:21:17'),('2002','測試廚師乙','chef2@example.com','chefpass','0912345678','[\"台中市\"]',NULL,'[\"西式料理\", \"甜點\"]','台中市西區公益路二段51號','2025-05-30 18:03:18');
/*!40000 ALTER TABLE `Chef` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Customer`
--

DROP TABLE IF EXISTS `Customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Customer` (
  `id` varchar(10) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `phone` varchar(15) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `phone_UNIQUE` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Customer`
--

LOCK TABLES `Customer` WRITE;
/*!40000 ALTER TABLE `Customer` DISABLE KEYS */;
INSERT INTO `Customer` VALUES ('1001','郭宗翰','11336014@ntub.edu.tw','aa0937404883','0937404883','2025-04-22 08:31:13'),('1002','測試顧客二號','customer2@example.com','password123','0987654321','2025-05-30 18:03:11');
/*!40000 ALTER TABLE `Customer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `OrderItems`
--

DROP TABLE IF EXISTS `OrderItems`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `OrderItems` (
  `order_item_id` int NOT NULL AUTO_INCREMENT,
  `order_id` varchar(12) NOT NULL,
  `dish_name` varchar(255) NOT NULL,
  `quantity` int NOT NULL DEFAULT '1',
  `required_ingredients` text,
  `cooking_method` varchar(100) DEFAULT NULL,
  `seasoning_preferences` text,
  `custom_notes` text,
  `chef_estimated_price_per_dish` int DEFAULT NULL,
  `chef_final_price_per_dish` int DEFAULT NULL,
  PRIMARY KEY (`order_item_id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `OrderItems_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `Orders` (`order_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `OrderItems`
--

LOCK TABLES `OrderItems` WRITE;
/*!40000 ALTER TABLE `OrderItems` DISABLE KEYS */;
INSERT INTO `OrderItems` VALUES (3,'202505180001','香煎鮭魚佐蘆筍',1,'鮭魚, 蘆筍, 檸檬, 橄欖油','油煎','{\"鹹度\": \"適中\", \"辣度\": \"不辣\"}','希望鮭魚不要太熟',300,NULL),(4,'202505180001','奶油蘑菇濃湯',2,'蘑菇, 鮮奶油, 洋蔥, 大蒜','燉煮','{\"鹹度\": \"適中\"}',NULL,150,NULL),(5,'202505180002','紅燒獅子頭',4,'豬絞肉, 大白菜, 醬油, 薑','紅燒','{\"鹹度\": \"鹹一點\", \"油度\":\"少油\"}','白菜燉爛一點',400,380),(6,'202505180003','清蒸鱸魚',1,'鱸魚, 蔥, 薑, 醬油','清蒸','{\"鹹度\": \"清淡\"}','多放蔥薑',300,NULL),(7,'TEST0001','宮保雞丁',1,'雞肉、乾辣椒、花生','快炒','{\"辣度\":\"小辣\"}','花生多一點',160,NULL),(8,'TEST0001','番茄炒蛋',1,'番茄、雞蛋、蔥','炒','{\"鹹度\":\"適中\"}',NULL,130,NULL),(9,'TEST0003','三杯雞',1,'雞腿肉、薑片、麻油、醬油、九層塔','三杯','{\"口味\":\"重口味\"}','麻油多一點',NULL,NULL),(10,'TEST0003','清炒時蔬',1,'當季蔬菜','清炒',NULL,'少油',NULL,NULL),(11,'TEST0004','客家小炒',2,'魷魚、五花肉、豆干、芹菜','炒','{\"鹹度\":\"適中\"}',NULL,250,NULL),(12,'TEST0004','酸菜肚片湯',1,'豬肚、酸菜、薑絲','燉煮',NULL,'豬肚燉爛一點',300,NULL),(13,'TEST0005','紅酒燉牛肉',1,'牛肋條、紅酒、洋蔥、紅蘿蔔','燉煮','{\"鹹度\":\"適中\"}','希望牛肉軟爛',700,NULL),(14,'TEST0005','香蒜麵包',4,'法國長棍、大蒜、奶油','烤',NULL,'蒜味濃郁',125,NULL),(15,'TEST0006','麻油雞飯',2,'雞腿肉、麻油、薑片、糯米','炒飯','{\"口味\":\"補身\"}',NULL,200,190),(16,'TEST0006','枸杞高麗菜',1,'高麗菜、枸杞','清炒','{\"鹹度\":\"清淡\"}',NULL,150,140),(17,'TEST0006','香菇雞湯',1,'雞腿、香菇、薑片','燉湯',NULL,NULL,100,100),(18,'TEST0007','泰式檸檬魚',1,'鱸魚、檸檬、香茅、辣椒','清蒸','{\"辣度\":\"中辣\"}','魚新鮮一點',350,350),(19,'TEST0007','蝦醬空心菜',1,'空心菜、蝦醬','炒',NULL,NULL,150,150),(20,'TEST0008','佛跳牆 (小份)',1,'多種食材','燉',NULL,'料多實在',900,880),(21,'TEST0009','蒜泥白肉',1,'五花肉、蒜蓉醬油','水煮','{\"口味\":\"正常\"}',NULL,250,250),(22,'TEST0009','麻婆豆腐',1,'豆腐、豬絞肉、豆瓣醬','燴','{\"辣度\":\"小辣\"}','不要太油',200,200),(23,'TEST0009','白飯',3,NULL,NULL,NULL,NULL,100,100),(24,'TEST0010','親子丼',2,'雞肉、雞蛋、洋蔥、日式醬油','丼飯','{\"口味\":\"偏甜\"}','蛋半熟',200,200);
/*!40000 ALTER TABLE `OrderItems` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Orders`
--

DROP TABLE IF EXISTS `Orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Orders` (
  `order_id` varchar(12) NOT NULL,
  `customer_id` varchar(255) NOT NULL,
  `chef_id` varchar(255) NOT NULL,
  `order_submit_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `service_date` date NOT NULL,
  `service_time` time NOT NULL,
  `pickup_method` varchar(50) NOT NULL,
  `delivery_address` text,
  `order_status` varchar(100) NOT NULL,
  `initial_price_chef` int DEFAULT NULL,
  `customer_counter_price` int DEFAULT NULL,
  `customer_reason` text,
  `final_price_chef` int DEFAULT NULL,
  `chef_final_price_reason` varchar(255) DEFAULT NULL,
  `rejection_reason` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`order_id`),
  KEY `customer_id` (`customer_id`),
  KEY `chef_id` (`chef_id`),
  CONSTRAINT `Orders_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `Customer` (`id`),
  CONSTRAINT `Orders_ibfk_2` FOREIGN KEY (`chef_id`) REFERENCES `Chef` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Orders`
--

LOCK TABLES `Orders` WRITE;
/*!40000 ALTER TABLE `Orders` DISABLE KEYS */;
INSERT INTO `Orders` VALUES ('202505180001','1001','2001','2025-05-18 15:51:05','2025-05-18','18:00:00','外送','測試路一段123號','訂單已完成',450,NULL,NULL,450,NULL,NULL,'2025-05-18 15:51:05','2025-05-30 17:54:18'),('202505180002','1001','2001','2025-05-18 15:51:05','2025-05-19','19:30:00','自取',NULL,'廚師已確認，備餐中',400,350,'小刀',380,NULL,NULL,'2025-05-18 15:51:05','2025-05-30 17:24:45'),('202505180003','1001','2001','2025-05-18 15:51:05','2025-05-20','12:00:00','外送','測試大道777號','廚師已確認，備餐中',300,NULL,NULL,300,NULL,NULL,'2025-05-18 15:51:05','2025-05-30 15:54:16'),('TEST0001','1001','2001','2025-05-23 18:04:49','2025-06-01','12:00:00','外送','台北市信義區市府路1號','廚師已確認，備餐中',290,NULL,NULL,290,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:17:24'),('TEST0002','1002','2001','2025-05-24 18:04:49','2025-06-02','18:30:00','自取',NULL,'已拒絕',NULL,NULL,NULL,NULL,NULL,'今日已滿單，無法承接，敬請見諒。','2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0003','1001','2002','2025-05-25 18:04:49','2025-06-03','19:00:00','外送','新北市板橋區中山路一段161號','待估價',NULL,NULL,NULL,NULL,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:22:38'),('TEST0004','1002','2002','2025-05-26 18:04:49','2025-06-01','11:30:00','自取',NULL,'議價中-廚師估價',800,NULL,NULL,NULL,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0005','1001','2001','2025-05-27 18:04:49','2025-06-02','20:00:00','外送','台北市大安區羅斯福路四段1號','議價中-顧客回價',1200,1000,'希望可以打個折，預算有限。',NULL,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0006','1002','2001','2025-05-28 18:04:49','2025-06-03','17:00:00','自取',NULL,'議價中-廚師定價',650,600,'學生希望便宜一點',620,'已是優惠價，食材成本考量，請見諒。',NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0007','1001','2002','2025-05-29 18:04:49','2025-06-01','12:30:00','外送','台北市中山區南京東路三段209號','廚師已確認，備餐中',500,NULL,NULL,500,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0008','1002','2002','2025-05-29 18:04:49','2025-06-02','19:30:00','自取',NULL,'訂單已取消 (顧客最終拒絕)',900,850,'太貴了',880,'這是最後報價。',NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49'),('TEST0009','1001','2001','2025-05-30 10:04:49','2025-06-01','18:00:00','外送','台北市中正區重慶南路一段122號','訂單已完成',750,NULL,NULL,750,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:18:50'),('TEST0010','1002','2001','2025-05-28 18:04:49','2025-05-30','13:00:00','自取',NULL,'訂單已完成',400,NULL,NULL,400,NULL,NULL,'2025-05-30 18:04:49','2025-05-30 18:04:49');
/*!40000 ALTER TABLE `Orders` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-05-31  2:53:06
