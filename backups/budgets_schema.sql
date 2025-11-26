-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: budgets_db
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accounts_activeuser`
--

DROP TABLE IF EXISTS `accounts_activeuser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_activeuser` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `login_time` datetime(6) NOT NULL,
  `hashed_count` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `last_activity` datetime(6) NOT NULL,
  `user_ip` char(39) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `user_agent` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_active` tinyint(1) NOT NULL,
  `logout_time` datetime(6) DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `unique_user_session` (`user_id`) USING BTREE,
  KEY `accounts_activeuser_session_key_48b1d026` (`session_key`) USING BTREE,
  KEY `accounts_activeuser_login_time_3b4e1b1e` (`login_time`) USING BTREE,
  KEY `accounts_activeuser_last_activity_493e764f` (`last_activity`) USING BTREE,
  KEY `idx_user` (`user_id`) USING BTREE,
  KEY `idx_last_activity` (`last_activity`) USING BTREE,
  CONSTRAINT `accounts_activeuser_user_id_43ede48b_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `check_login_before_activity` CHECK ((`login_time` <= `last_activity`))
) ENGINE=InnoDB AUTO_INCREMENT=211 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_audit_log`
--

DROP TABLE IF EXISTS `accounts_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `view_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `method` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `model_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `changes` json DEFAULT NULL,
  `ip_address` char(39) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `browser` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status_code` int DEFAULT NULL,
  `related_object` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `accounts_audit_log_user_id_92f0051c_fk_accounts_customuser_id` (`user_id`) USING BTREE,
  CONSTRAINT `accounts_audit_log_user_id_92f0051c_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=21318 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_city`
--

DROP TABLE IF EXISTS `accounts_city`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_city` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_capital` tinyint(1) NOT NULL,
  `province_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `accounts_city_name_province_id_0f905959_uniq` (`name`,`province_id`) USING BTREE,
  KEY `accounts_city_province_id_3c87e1c3_fk_accounts_province_id` (`province_id`) USING BTREE,
  CONSTRAINT `accounts_city_province_id_3c87e1c3_fk_accounts_province_id` FOREIGN KEY (`province_id`) REFERENCES `accounts_province` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_customprofile`
--

DROP TABLE IF EXISTS `accounts_customprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_customprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `first_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `phone_number` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `birth_date` date DEFAULT NULL,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `location` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `bio` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `zip_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `theme` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `city_id` bigint DEFAULT NULL,
  `user_id` bigint NOT NULL,
  `province_id` bigint DEFAULT NULL,
  `custom_theme_data` json DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `user_id` (`user_id`) USING BTREE,
  KEY `accounts_customprofile_city_id_e241f232_fk_accounts_city_id` (`city_id`) USING BTREE,
  KEY `accounts_customprofi_province_id_76bdd0ef_fk_accounts_` (`province_id`) USING BTREE,
  CONSTRAINT `accounts_customprofi_province_id_76bdd0ef_fk_accounts_` FOREIGN KEY (`province_id`) REFERENCES `accounts_province` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customprofi_user_id_150416de_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customprofile_city_id_e241f232_fk_accounts_city_id` FOREIGN KEY (`city_id`) REFERENCES `accounts_city` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_customuser`
--

DROP TABLE IF EXISTS `accounts_customuser`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_customuser` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `email` varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `first_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `username` (`username`) USING BTREE,
  UNIQUE KEY `email` (`email`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_customuser_groups`
--

DROP TABLE IF EXISTS `accounts_customuser_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_customuser_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `mygroup_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `accounts_customuser__customuser_id_bc55088e_fk_accounts_` (`customuser_id`) USING BTREE,
  KEY `accounts_customuser__mygroup_id_e98a3018_fk_accounts_` (`mygroup_id`) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_bc55088e_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser__mygroup_id_e98a3018_fk_accounts_` FOREIGN KEY (`mygroup_id`) REFERENCES `accounts_mygroups` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_customuser_roles`
--

DROP TABLE IF EXISTS `accounts_customuser_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_customuser_roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `accounts_customuser_roles_customuser_id_role_id_4c344b94_uniq` (`customuser_id`,`role_id`) USING BTREE,
  KEY `accounts_customuser_roles_role_id_e0ee129a_fk_accounts_role_id` (`role_id`) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_737b4b7e_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser_roles_role_id_e0ee129a_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_customuser_user_permissions`
--

DROP TABLE IF EXISTS `accounts_customuser_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_customuser_user_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `accounts_customuser_user_customuser_id_permission_9632a709_uniq` (`customuser_id`,`permission_id`) USING BTREE,
  KEY `accounts_customuser__permission_id_aea3d0e5_fk_auth_perm` (`permission_id`) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_0deaefae_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser__permission_id_aea3d0e5_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=455 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_mygroups`
--

DROP TABLE IF EXISTS `accounts_mygroups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_mygroups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `name` (`name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_mygroups_roles`
--

DROP TABLE IF EXISTS `accounts_mygroups_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_mygroups_roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `mygroup_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `accounts_mygroups_roles_mygroup_id_role_id_fd84a847_uniq` (`mygroup_id`,`role_id`) USING BTREE,
  KEY `accounts_mygroups_roles_role_id_6c64e294_fk_accounts_role_id` (`role_id`) USING BTREE,
  CONSTRAINT `accounts_mygroups_ro_mygroup_id_0e3dee22_fk_accounts_` FOREIGN KEY (`mygroup_id`) REFERENCES `accounts_mygroups` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_mygroups_roles_role_id_6c64e294_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_province`
--

DROP TABLE IF EXISTS `accounts_province`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_province` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `name` (`name`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_role`
--

DROP TABLE IF EXISTS `accounts_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_active` tinyint(1) NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `name` (`name`) USING BTREE,
  KEY `accounts_role_parent_id_526243b4_fk_accounts_role_id` (`parent_id`) USING BTREE,
  CONSTRAINT `accounts_role_parent_id_526243b4_fk_accounts_role_id` FOREIGN KEY (`parent_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_role_permissions`
--

DROP TABLE IF EXISTS `accounts_role_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_role_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `accounts_role_permissions_role_id_permission_id_032c715e_uniq` (`role_id`,`permission_id`) USING BTREE,
  KEY `accounts_role_permis_permission_id_76fe677d_fk_auth_perm` (`permission_id`) USING BTREE,
  CONSTRAINT `accounts_role_permis_permission_id_76fe677d_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_role_permissions_role_id_54f107a6_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=2186 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `accounts_timelockmodel`
--

DROP TABLE IF EXISTS `accounts_timelockmodel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_timelockmodel` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `lock_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `hash_value` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `salt` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `organization_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `hash_value` (`hash_value`) USING BTREE,
  UNIQUE KEY `salt` (`salt`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `admin_interface_theme`
--

DROP TABLE IF EXISTS `admin_interface_theme`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin_interface_theme` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `active` tinyint(1) NOT NULL,
  `title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `title_visible` tinyint(1) NOT NULL,
  `logo` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `logo_visible` tinyint(1) NOT NULL,
  `css_header_background_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `title_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_header_text_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_header_link_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_header_link_hover_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_background_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_text_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_link_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_link_hover_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_rounded_corners` tinyint(1) NOT NULL,
  `css_generic_link_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_generic_link_hover_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_save_button_background_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_save_button_background_hover_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_save_button_text_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_delete_button_background_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_delete_button_background_hover_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_delete_button_text_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `list_filter_dropdown` tinyint(1) NOT NULL,
  `related_modal_active` tinyint(1) NOT NULL,
  `related_modal_background_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `related_modal_rounded_corners` tinyint(1) NOT NULL,
  `logo_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `recent_actions_visible` tinyint(1) NOT NULL,
  `favicon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `related_modal_background_opacity` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `env_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `env_visible_in_header` tinyint(1) NOT NULL,
  `env_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `env_visible_in_favicon` tinyint(1) NOT NULL,
  `related_modal_close_button_visible` tinyint(1) NOT NULL,
  `language_chooser_active` tinyint(1) NOT NULL,
  `language_chooser_display` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `list_filter_sticky` tinyint(1) NOT NULL,
  `form_pagination_sticky` tinyint(1) NOT NULL,
  `form_submit_sticky` tinyint(1) NOT NULL,
  `css_module_background_selected_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `css_module_link_selected_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `logo_max_height` smallint unsigned NOT NULL,
  `logo_max_width` smallint unsigned NOT NULL,
  `foldable_apps` tinyint(1) NOT NULL,
  `language_chooser_control` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `list_filter_highlight` tinyint(1) NOT NULL,
  `list_filter_removal_links` tinyint(1) NOT NULL,
  `show_fieldsets_as_tabs` tinyint(1) NOT NULL,
  `show_inlines_as_tabs` tinyint(1) NOT NULL,
  `css_generic_link_active_color` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `collapsible_stacked_inlines` tinyint(1) NOT NULL,
  `collapsible_stacked_inlines_collapsed` tinyint(1) NOT NULL,
  `collapsible_tabular_inlines` tinyint(1) NOT NULL,
  `collapsible_tabular_inlines_collapsed` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `admin_interface_theme_name_30bda70f_uniq` (`name`) USING BTREE,
  CONSTRAINT `admin_interface_theme_chk_1` CHECK ((`logo_max_height` >= 0)),
  CONSTRAINT `admin_interface_theme_chk_2` CHECK ((`logo_max_width` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `name` (`name`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`) USING BTREE,
  KEY `auth_group_permissions_permission_id_84c5c92e_fk` (`permission_id`) USING BTREE,
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `auth_group_permissions_permission_id_84c5c92e_fk` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`) USING BTREE,
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=377 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgetallocation`
--

DROP TABLE IF EXISTS `budgets_budgetallocation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgetallocation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `allocated_amount` decimal(25,2) NOT NULL,
  `allocation_date` date NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `budget_period_id` bigint NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `project_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `allocation_number` int NOT NULL,
  `is_stopped` tinyint(1) NOT NULL,
  `locked_percentage` decimal(5,2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `warning_threshold` decimal(5,2) NOT NULL,
  `returned_amount` decimal(25,2) NOT NULL,
  `budget_item_id` bigint DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  `subproject_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `budgets_budgetalloca_created_by_id_8203e930_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `budgets_bud_budget__3d5534_idx` (`budget_period_id`,`allocation_date`) USING BTREE,
  KEY `budgets_bud_organiz_05ceb0_idx` (`organization_id`,`allocated_amount`) USING BTREE,
  KEY `budgets_budgetallocation_project_id_d67ab494_fk_core_project_id` (`project_id`) USING BTREE,
  CONSTRAINT `budgets_budgetalloca_budget_period_id_08592985_fk_budgets_b` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetalloca_created_by_id_8203e930_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetalloca_organization_id_3b329857_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetallocation_project_id_d67ab494_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=98 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgethistory`
--

DROP TABLE IF EXISTS `budgets_budgethistory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgethistory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int unsigned NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25,2) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `transaction_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `content_type_id` int NOT NULL,
  `transaction_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `transaction_id` (`transaction_id`) USING BTREE,
  KEY `budgets_budgethistor_created_by_id_c66a36b4_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `budgets_budgethistor_content_type_id_2a837fe7_fk_django_co` (`content_type_id`) USING BTREE,
  CONSTRAINT `budgets_budgethistor_content_type_id_2a837fe7_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgethistor_created_by_id_c66a36b4_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgethistory_chk_1` CHECK ((`object_id` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=72 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgetitem`
--

DROP TABLE IF EXISTS `budgets_budgetitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgetitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `budget_period_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `create_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE,
  UNIQUE KEY `uq_budgetitem_period_org_code` (`budget_period_id`,`organization_id`,`code`) USING BTREE,
  KEY `fk_budgetitem_organization` (`organization_id`) USING BTREE,
  CONSTRAINT `fk_budgetitem_budgetperiod` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_budgetitem_organization` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgetperiod`
--

DROP TABLE IF EXISTS `budgets_budgetperiod`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgetperiod` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `total_amount` decimal(25,0) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `lock_condition` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `locked_percentage` int NOT NULL,
  `warning_threshold` decimal(5,2) NOT NULL,
  `is_completed` tinyint(1) NOT NULL,
  `total_allocated` decimal(25,2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_phase` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `returned_amount` decimal(25,2) NOT NULL,
  `is_period_locked` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `budgets_budgetperiod_name_01bedea2_uniq` (`name`) USING BTREE,
  KEY `IX_BudgetPeriod_organization_id` (`organization_id`) USING BTREE,
  KEY `IX_BudgetPeriod_created_by_id` (`created_by_id`) USING BTREE,
  KEY `IX_BudgetPeriod_Dates` (`start_date`,`end_date`) USING BTREE,
  CONSTRAINT `budgets_budgetperiod_created_by_id_487cfefd_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetperiod_organization_id_fa17309e_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgetreallocation`
--

DROP TABLE IF EXISTS `budgets_budgetreallocation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgetreallocation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `amount` decimal(25,2) NOT NULL,
  `reallocation_date` date NOT NULL,
  `reason` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `source_allocation_id` bigint NOT NULL,
  `target_allocation_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `budgets_budgetreallo_source_allocation_id_d454eec2_fk_budgets_b` (`source_allocation_id`) USING BTREE,
  KEY `budgets_budgetreallo_target_allocation_id_e57b016e_fk_budgets_b` (`target_allocation_id`) USING BTREE,
  KEY `budgets_budgetreallo_created_by_id_931b064f_fk_accounts_` (`created_by_id`) USING BTREE,
  CONSTRAINT `budgets_budgetreallo_created_by_id_931b064f_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetreallo_source_allocation_id_d454eec2_fk_budgets_b` FOREIGN KEY (`source_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetreallo_target_allocation_id_e57b016e_fk_budgets_b` FOREIGN KEY (`target_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgetsettings`
--

DROP TABLE IF EXISTS `budgets_budgetsettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgetsettings` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `level` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `locked_percentage` decimal(5,2) NOT NULL,
  `warning_threshold` decimal(5,2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `budget_period_id` bigint DEFAULT NULL,
  `organization_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `budgets_budgetsettin_budget_period_id_4d876a4b_fk_budgets_b` (`budget_period_id`) USING BTREE,
  KEY `budgets_budgetsettin_organization_id_4597e0aa_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `budgets_budgetsettin_budget_period_id_4d876a4b_fk_budgets_b` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetsettin_organization_id_4597e0aa_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgettransaction`
--

DROP TABLE IF EXISTS `budgets_budgettransaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgettransaction` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `transaction_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25,2) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_id` bigint DEFAULT NULL,
  `related_tankhah_id` bigint DEFAULT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `transaction_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `client_host` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `client_ip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `related_factor_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `transaction_id` (`transaction_id`) USING BTREE,
  KEY `budgets_budgettransa_allocation_id_3ea01a6b_fk_budgets_b` (`allocation_id`) USING BTREE,
  KEY `budgets_budgettransa_related_tankhah_id_9dbc06de_fk_tankhah_t` (`related_tankhah_id`) USING BTREE,
  KEY `budgets_budgettransa_created_by_id_30bcb59a_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `budgets_budgettransa_related_factor_id_193681d2_fk_tankhah_f` (`related_factor_id`) USING BTREE,
  CONSTRAINT `budgets_budgettransa_allocation_id_3ea01a6b_fk_budgets_b` FOREIGN KEY (`allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_created_by_id_30bcb59a_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_related_factor_id_193681d2_fk_tankhah_f` FOREIGN KEY (`related_factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_related_tankhah_id_9dbc06de_fk_tankhah_t` FOREIGN KEY (`related_tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=178 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_budgettransferreturn`
--

DROP TABLE IF EXISTS `budgets_budgettransferreturn`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_budgettransferreturn` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_costcenter`
--

DROP TABLE IF EXISTS `budgets_costcenter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_costcenter` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocated_budget` decimal(25,2) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `budget_allocation_id` bigint NOT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE,
  KEY `budgets_costcenter_budget_allocation_id_1f2c1ba7_fk_budgets_b` (`budget_allocation_id`) USING BTREE,
  KEY `budgets_costcenter_organization_id_3ffab0d4_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `budgets_costcenter_budget_allocation_id_1f2c1ba7_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_costcenter_organization_id_3ffab0d4_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_payee`
--

DROP TABLE IF EXISTS `budgets_payee`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_payee` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `payee_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `national_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `account_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `iban` varchar(34) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `family` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `legal_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `brand_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `tax_id` varbinary(20) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `budgets_payee_created_by_id_7753d727_fk_accounts_customuser_id` (`created_by_id`) USING BTREE,
  CONSTRAINT `budgets_payee_created_by_id_7753d727_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_paymentorder`
--

DROP TABLE IF EXISTS `budgets_paymentorder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_paymentorder` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `issue_date` date NOT NULL,
  `amount` decimal(25,2) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `payment_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `status_id` int NOT NULL,
  `min_signatures` int NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `created_by_post_id` bigint DEFAULT NULL,
  `payee_id` bigint DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  `payment_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `is_active` tinyint DEFAULT NULL,
  `related_tankhah_id` tinyint DEFAULT NULL,
  `payee_account_number` bigint DEFAULT NULL,
  `payee_iban` bigint DEFAULT NULL,
  `payment_tracking_id` tinyint DEFAULT NULL,
  `paid_by_id` tinyint DEFAULT NULL,
  `organization_id` tinyint DEFAULT NULL,
  `project_id` tinyint DEFAULT NULL,
  `current_stage_id` tinyint DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_locked` float DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_archived` float DEFAULT NULL,
  `archived_at` tinyint DEFAULT NULL,
  `archived_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `order_number` (`order_number`) USING BTREE,
  KEY `budgets_paymentorder_created_by_id_1c9df5c8_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `budgets_paymentorder_created_by_post_id_8e17276f_fk_core_post_id` (`created_by_post_id`) USING BTREE,
  KEY `budgets_paymentorder_payee_id_6ac4b2b3_fk_budgets_payee_id` (`payee_id`) USING BTREE,
  KEY `budgets_paymentorder_tankhah_id_0a90ef8c_fk_tankhah_tankhah_id` (`tankhah_id`) USING BTREE,
  KEY `budgets_pay_status__7a985f_idx` (`status_id`,`organization_id`) USING BTREE,
  KEY `budgets_pay_is_arch_415832_idx` (`is_archived`,`is_locked`) USING BTREE,
  CONSTRAINT `budgets_paymentorder_created_by_id_1c9df5c8_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_created_by_post_id_8e17276f_fk_core_post_id` FOREIGN KEY (`created_by_post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_payee_id_6ac4b2b3_fk_budgets_payee_id` FOREIGN KEY (`payee_id`) REFERENCES `budgets_payee` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_tankhah_id_0a90ef8c_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_paymentorder_related_factors`
--

DROP TABLE IF EXISTS `budgets_paymentorder_related_factors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_paymentorder_related_factors` (
  `id` int NOT NULL AUTO_INCREMENT,
  `paymentorder_id` bigint NOT NULL,
  `factor_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `budgets_paymentorder_rel_paymentorder_id_factor_i_f798b702_uniq` (`paymentorder_id`,`factor_id`) USING BTREE,
  KEY `budgets_paymentorder_factor_id_66eb4c75_fk_tankhah_f` (`factor_id`) USING BTREE,
  CONSTRAINT `budgets_paymentorder_factor_id_66eb4c75_fk_tankhah_f` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_paymentorder_id_85be9196_fk_budgets_p` FOREIGN KEY (`paymentorder_id`) REFERENCES `budgets_paymentorder` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_projectbudgetallocation`
--

DROP TABLE IF EXISTS `budgets_projectbudgetallocation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_projectbudgetallocation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `allocated_amount` decimal(25,2) NOT NULL,
  `allocation_date` date NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `budget_allocation_id` bigint NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `project_id` bigint NOT NULL,
  `subproject_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `returned_amount` decimal(25,2) DEFAULT NULL,
  `is_locked` tinyint(1) DEFAULT NULL,
  `locked_percentage` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `budgets_projectbudge_budget_allocation_id_4605121d_fk_budgets_b` (`budget_allocation_id`) USING BTREE,
  KEY `budgets_projectbudge_created_by_id_a7e2ba3a_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `budgets_pro_project_86d725_idx` (`project_id`) USING BTREE,
  KEY `budgets_pro_subproj_9a9505_idx` (`subproject_id`) USING BTREE,
  CONSTRAINT `budgets_projectbudge_budget_allocation_id_4605121d_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_created_by_id_a7e2ba3a_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_project_id_7606ae30_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_subproject_id_6210df4a_fk_core_subp` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `budgets_transactiontype`
--

DROP TABLE IF EXISTS `budgets_transactiontype`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `budgets_transactiontype` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `requires_extra_approval` tinyint(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `transaction_flow` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `name` (`name`) USING BTREE,
  KEY `budgets_transactiont_created_by_id_bf8f9755_fk_accounts_` (`created_by_id`) USING BTREE,
  CONSTRAINT `budgets_transactiont_created_by_id_bf8f9755_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_accessrule`
--

DROP TABLE IF EXISTS `core_accessrule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_accessrule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `organization_id` bigint DEFAULT NULL,
  `branch_id` int DEFAULT NULL,
  `stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `action_type` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_payment_order_signer` float DEFAULT NULL,
  `is_active` float DEFAULT NULL,
  `entity_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `post_id` bigint DEFAULT NULL,
  `min_signatures` int unsigned NOT NULL,
  `auto_advance` tinyint(1) NOT NULL,
  `is_final_stage` tinyint(1) NOT NULL,
  `stage_order` int unsigned DEFAULT NULL,
  `triggers_payment_order` tinyint(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `min_level` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_accessrule_post_id_9e70516e_fk_core_post_id` (`post_id`) USING BTREE,
  KEY `core_accessrule_created_by_id_76af7d97_fk_accounts_customuser_id` (`created_by_id`) USING BTREE,
  CONSTRAINT `core_accessrule_created_by_id_76af7d97_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_accessrule_post_id_9e70516e_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_accessrule_chk_1` CHECK ((`min_signatures` >= 0)),
  CONSTRAINT `core_accessrule_chk_2` CHECK ((`stage_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6049 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_action`
--

DROP TABLE IF EXISTS `core_action`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_action` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_by_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime(6) NOT NULL,
  `button_style` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `confirmation_message` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `icon` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_branch`
--

DROP TABLE IF EXISTS `core_branch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_branch` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_dashboard_core`
--

DROP TABLE IF EXISTS `core_dashboard_core`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_dashboard_core` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_dashboardview`
--

DROP TABLE IF EXISTS `core_dashboardview`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_dashboardview` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_dashboardview_flows`
--

DROP TABLE IF EXISTS `core_dashboardview_flows`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_dashboardview_flows` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_dashboardwidgetpermissions`
--

DROP TABLE IF EXISTS `core_dashboardwidgetpermissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_dashboardwidgetpermissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_dynamicconfiguration`
--

DROP TABLE IF EXISTS `core_dynamicconfiguration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_dynamicconfiguration` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `key` (`key`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_fontsettings`
--

DROP TABLE IF EXISTS `core_fontsettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_fontsettings` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `family_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_file` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_format` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_weight` int NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `is_rtl_support` tinyint(1) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `file_size` int unsigned DEFAULT NULL,
  `upload_date` datetime(6) NOT NULL,
  `uploaded_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_fontsettings_uploaded_by_id_7b218a45_fk_accounts_` (`uploaded_by_id`) USING BTREE,
  CONSTRAINT `core_fontsettings_uploaded_by_id_7b218a45_fk_accounts_` FOREIGN KEY (`uploaded_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_fontsettings_chk_1` CHECK ((`file_size` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_organization`
--

DROP TABLE IF EXISTS `core_organization`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_organization` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `org_type_id` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `parent_organization_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_core` tinyint(1) NOT NULL,
  `is_independent` float DEFAULT NULL,
  `is_holding` float DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE,
  KEY `core_organi_code_eadc65_idx` (`code`,`org_type_id`) USING BTREE,
  KEY `core_organization_parent_organization__0e5b8fdd_fk_core_orga` (`parent_organization_id`) USING BTREE,
  CONSTRAINT `core_organization_parent_organization__0e5b8fdd_fk_core_orga` FOREIGN KEY (`parent_organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_organizationchartapiview`
--

DROP TABLE IF EXISTS `core_organizationchartapiview`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_organizationchartapiview` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_organizationchartview`
--

DROP TABLE IF EXISTS `core_organizationchartview`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_organizationchartview` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_organizationtype`
--

DROP TABLE IF EXISTS `core_organizationtype`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_organizationtype` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `org_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `fname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_budget_allocatable` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `en_name` (`org_type`) USING BTREE,
  UNIQUE KEY `fname` (`fname`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_permission_allowed_actions`
--

DROP TABLE IF EXISTS `core_permission_allowed_actions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_permission_allowed_actions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `permission_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_post`
--

DROP TABLE IF EXISTS `core_post`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_post` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `level` int NOT NULL,
  `branch_id` varchar(3) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_active` tinyint(1) NOT NULL,
  `organization_id` bigint NOT NULL,
  `parent_id` bigint DEFAULT NULL,
  `max_change_level` int NOT NULL,
  `is_payment_order_signer` tinyint(1) NOT NULL,
  `can_final_approve_budget` tinyint(1) NOT NULL,
  `can_final_approve_factor` tinyint(1) NOT NULL,
  `can_final_approve_tankhah` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_post_organization_id_7cb921cb_fk_core_organization_id` (`organization_id`) USING BTREE,
  KEY `core_post_parent_id_f52ad6c0_fk_core_post_id` (`parent_id`) USING BTREE,
  CONSTRAINT `core_post_organization_id_7cb921cb_fk_core_organization_id` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_post_parent_id_f52ad6c0_fk_core_post_id` FOREIGN KEY (`parent_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=46 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_postaction`
--

DROP TABLE IF EXISTS `core_postaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_postaction` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `post_id` bigint NOT NULL,
  `stage_id` bigint NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `triggers_payment_order` tinyint(1) NOT NULL,
  `min_level` int DEFAULT NULL,
  `allowed_actions` json NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_postaction_stage_id_e86eeb7d_fk_core_workflowstage_id` (`stage_id`) USING BTREE,
  KEY `core_postaction_post_id_27e16c7b` (`post_id`) USING BTREE,
  CONSTRAINT `core_postaction_post_id_27e16c7b_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_posthistory`
--

DROP TABLE IF EXISTS `core_posthistory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_posthistory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `changed_field` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `old_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `new_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `changed_at` datetime(6) NOT NULL,
  `changed_by_id` bigint DEFAULT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_posthistory_changed_by_id_56e23fbe_fk_accounts_` (`changed_by_id`) USING BTREE,
  KEY `core_posthi_post_id_2c35ae_idx` (`post_id`,`changed_at`) USING BTREE,
  CONSTRAINT `core_posthistory_changed_by_id_56e23fbe_fk_accounts_` FOREIGN KEY (`changed_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_posthistory_post_id_06bedfe1_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=286 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_postruleassignment`
--

DROP TABLE IF EXISTS `core_postruleassignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_postruleassignment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `custom_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `post_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  `organization_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_postruleassignm_created_by_id_5a5a4ae7_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `core_postruleassignment_post_id_4638abbc` (`post_id`) USING BTREE,
  KEY `core_postruleassignment_action_id_9e94943b_fk_core_action_id` (`action_id`) USING BTREE,
  KEY `core_postruleassignm_organization_id_bd603b1a_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `core_postruleassignm_created_by_id_5a5a4ae7_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignm_organization_id_bd603b1a_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignment_action_id_9e94943b_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignment_post_id_4638abbc_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=1343 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_project`
--

DROP TABLE IF EXISTS `core_project`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_project` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_active` tinyint(1) NOT NULL,
  `allocations_id` bigint DEFAULT NULL,
  `priority` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_project_organizations`
--

DROP TABLE IF EXISTS `core_project_organizations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_project_organizations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `core_project_organizatio_project_id_organization__629c5e5f_uniq` (`project_id`,`organization_id`) USING BTREE,
  KEY `core_project_organiz_organization_id_2397ad59_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `core_project_organiz_organization_id_2397ad59_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_project_organiz_project_id_235f1848_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_status`
--

DROP TABLE IF EXISTS `core_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_status` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_initial` tinyint(1) NOT NULL,
  `is_final_approve` tinyint(1) NOT NULL,
  `is_final_reject` tinyint(1) NOT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `created_by_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime(6) NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_paid` tinyint(1) NOT NULL,
  `is_pending` tinyint(1) NOT NULL,
  `is_rejected` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE,
  KEY `core_status_code_d5fe62_idx` (`code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_subproject`
--

DROP TABLE IF EXISTS `core_subproject`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_subproject` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `is_active` tinyint(1) NOT NULL,
  `project_id` bigint NOT NULL,
  `allocated_budget` decimal(25,2) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_subproject_project_id_07e5e283_fk_core_project_id` (`project_id`) USING BTREE,
  CONSTRAINT `core_subproject_project_id_07e5e283_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_systemsettings`
--

DROP TABLE IF EXISTS `core_systemsettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_systemsettings` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `budget_locked_percentage_default` decimal(5,2) NOT NULL,
  `budget_warning_threshold_default` decimal(5,2) NOT NULL,
  `budget_warning_action_default` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_locked_percentage_default` decimal(5,2) NOT NULL,
  `tankhah_used_statuses` json NOT NULL,
  `tankhah_accessible_organizations` json NOT NULL,
  `tankhah_payment_ceiling_default` decimal(25,0) DEFAULT NULL,
  `tankhah_payment_ceiling_enabled_default` tinyint(1) DEFAULT NULL,
  `allow_action_without_org_chart` tinyint(1) NOT NULL,
  `allow_bypass_org_chart` tinyint(1) NOT NULL,
  `enforce_strict_approval_order` tinyint(1) NOT NULL,
  `enforce_single_browser_session` tinyint(1) NOT NULL,
  `enforce_single_tab` tinyint(1) NOT NULL,
  `heartbeat_interval_ms` int NOT NULL,
  `heartbeat_stale_ms` int NOT NULL,
  `allow_tankhah_budget_overrun` tinyint(1) NOT NULL,
  `lock_period_after_expiry_enforce_on_write_only` tinyint(1) NOT NULL,
  `allow_factor_budget_overrun` tinyint(1) NOT NULL,
  `factor_payment_ceiling_default` decimal(25,2) DEFAULT NULL,
  `factor_payment_ceiling_enabled_default` tinyint(1) NOT NULL,
  `enforce_tankhah_ceiling_on_factor` tinyint(1) NOT NULL,
  `exclude_expired_tankhah_from_factor_form` tinyint(1) NOT NULL,
  `create_budget_commitment_on_factor_draft` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_transition`
--

DROP TABLE IF EXISTS `core_transition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_transition` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  `from_status_id` bigint NOT NULL,
  `to_status_id` bigint NOT NULL,
  `created_by_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `is_active` tinyint(1) DEFAULT '1',
  `organization_id` int DEFAULT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_transition_action_id_b287ea45_fk_core_action_id` (`action_id`) USING BTREE,
  KEY `core_transition_from_status_id_7c70969a_fk_core_status_id` (`from_status_id`) USING BTREE,
  KEY `core_transition_to_status_id_5eaef663_fk_core_status_id` (`to_status_id`) USING BTREE,
  KEY `core_transition_entity_type_id_1043c22c` (`entity_type_id`) USING BTREE,
  KEY `core_transi_entity__5109ac_idx` (`entity_type_id`,`organization_id`,`from_status_id`,`is_active`) USING BTREE,
  KEY `core_transition_organization_id_c6a6b401` (`organization_id`) USING BTREE,
  CONSTRAINT `core_transition_action_id_b287ea45_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_from_status_id_7c70969a_fk_core_status_id` FOREIGN KEY (`from_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_to_status_id_5eaef663_fk_core_status_id` FOREIGN KEY (`to_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=729 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_transition_allowed_posts`
--

DROP TABLE IF EXISTS `core_transition_allowed_posts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_transition_allowed_posts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `transition_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `core_transition_allowed__transition_id_post_id_bf5dd99e_uniq` (`transition_id`,`post_id`) USING BTREE,
  KEY `core_transition_allowed_posts_post_id_3c2cc5d5_fk_core_post_id` (`post_id`) USING BTREE,
  CONSTRAINT `core_transition_allo_transition_id_70ee581d_fk_core_tran` FOREIGN KEY (`transition_id`) REFERENCES `core_transition` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_allowed_posts_post_id_3c2cc5d5_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=1516 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_transitiontemplate`
--

DROP TABLE IF EXISTS `core_transitiontemplate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_transitiontemplate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name_template` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `action_id` bigint NOT NULL,
  `created_by_id` bigint NOT NULL,
  `entity_type_id` bigint NOT NULL,
  `from_status_id` bigint NOT NULL,
  `to_status_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `core_transitiontemplate_entity_type_id_action_id_06fa0bbb_uniq` (`entity_type_id`,`action_id`) USING BTREE,
  KEY `core_transitiontemplate_action_id_03ee8f6d_fk_core_action_id` (`action_id`) USING BTREE,
  KEY `core_transitiontempl_created_by_id_cd56ddf6_fk_accounts_` (`created_by_id`) USING BTREE,
  CONSTRAINT `core_transitiontempl_created_by_id_cd56ddf6_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transitiontemplate_action_id_03ee8f6d_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_userpost`
--

DROP TABLE IF EXISTS `core_userpost`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_userpost` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `start_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `post_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_userpost_post_id_3da85c9b_fk_core_post_id` (`post_id`) USING BTREE,
  KEY `core_userpost_user_id_d7e77eae` (`user_id`) USING BTREE,
  CONSTRAINT `core_userpost_post_id_3da85c9b_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_userpost_user_id_d7e77eae_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_userruleoverride`
--

DROP TABLE IF EXISTS `core_userruleoverride`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_userruleoverride` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_enabled` tinyint(1) NOT NULL,
  `notes` varchar(255) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `action_id` bigint NOT NULL,
  `entity_type_id` bigint NOT NULL,
  `organization_id` bigint NOT NULL,
  `post_id` bigint DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `core_userruleoverride_user_id_organization_id__5b4340cb_uniq` (`user_id`,`organization_id`,`action_id`,`entity_type_id`,`post_id`),
  KEY `core_userruleoverride_action_id_6fa0cb1d_fk_core_action_id` (`action_id`),
  KEY `core_userruleoverrid_entity_type_id_834def85_fk_core_enti` (`entity_type_id`),
  KEY `core_userruleoverrid_organization_id_ae74f642_fk_core_orga` (`organization_id`),
  KEY `core_userruleoverride_post_id_5e324d13_fk_core_post_id` (`post_id`),
  CONSTRAINT `core_userruleoverrid_entity_type_id_834def85_fk_core_enti` FOREIGN KEY (`entity_type_id`) REFERENCES `core_entitytype` (`id`),
  CONSTRAINT `core_userruleoverrid_organization_id_ae74f642_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`),
  CONSTRAINT `core_userruleoverride_action_id_6fa0cb1d_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`),
  CONSTRAINT `core_userruleoverride_post_id_5e324d13_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`),
  CONSTRAINT `core_userruleoverride_user_id_94f4abd0_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_workflowruletemplate`
--

DROP TABLE IF EXISTS `core_workflowruletemplate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_workflowruletemplate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `rules_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_public` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_workflowruletem_created_by_id_182ee905_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `core_workflowruletem_organization_id_b77b7a7e_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `core_workflowruletem_created_by_id_182ee905_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_workflowruletem_organization_id_b77b7a7e_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `core_workflowstage`
--

DROP TABLE IF EXISTS `core_workflowstage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_workflowstage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `order` int unsigned NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_final_stage` tinyint(1) NOT NULL,
  `triggers_payment_order` float DEFAULT NULL,
  `auto_advance` float DEFAULT NULL,
  `entity_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `min_signatures` int unsigned NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `core_workflowstage_entity_type_238ea13d` (`entity_type`) USING BTREE,
  KEY `core_workfl_entity__89d262_idx` (`entity_type`,`is_active`) USING BTREE,
  CONSTRAINT `core_workflowstage_chk_1` CHECK ((`min_signatures` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `object_repr` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_customuser_id` (`user_id`) USING BTREE,
  KEY `django_admin_log_content_type_id_c4bce8eb_fk` (`content_type_id`) USING BTREE,
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=55 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=159 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=366 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `session_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`) USING BTREE,
  KEY `django_session_expire_date_a5c62663` (`expire_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_backuplog`
--

DROP TABLE IF EXISTS `notificationApp_backuplog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_backuplog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `status` varchar(20) NOT NULL,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6) DEFAULT NULL,
  `duration` bigint DEFAULT NULL,
  `file_size` bigint DEFAULT NULL,
  `file_path` varchar(500) DEFAULT NULL,
  `error_message` longtext,
  `details` json NOT NULL,
  `schedule_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `notificationApp_back_schedule_id_90087260_fk_notificat` (`schedule_id`),
  CONSTRAINT `notificationApp_back_schedule_id_90087260_fk_notificat` FOREIGN KEY (`schedule_id`) REFERENCES `notificationApp_backupschedule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_backupschedule`
--

DROP TABLE IF EXISTS `notificationApp_backupschedule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_backupschedule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `description` longtext,
  `frequency` varchar(20) NOT NULL,
  `custom_cron` varchar(100) DEFAULT NULL,
  `database` varchar(10) NOT NULL,
  `format_type` varchar(10) NOT NULL,
  `encrypt` tinyint(1) NOT NULL,
  `password` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `last_run` datetime(6) DEFAULT NULL,
  `next_run` datetime(6) DEFAULT NULL,
  `notify_on_success` tinyint(1) NOT NULL,
  `notify_on_failure` tinyint(1) NOT NULL,
  `created_by_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `notificationApp_back_created_by_id_5e101a27_fk_accounts_` (`created_by_id`),
  CONSTRAINT `notificationApp_back_created_by_id_5e101a27_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_backupschedule_notify_recipients`
--

DROP TABLE IF EXISTS `notificationApp_backupschedule_notify_recipients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_backupschedule_notify_recipients` (
  `id` int NOT NULL AUTO_INCREMENT,
  `backupschedule_id` bigint NOT NULL,
  `customuser_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `notificationApp_backupsc_backupschedule_id_custom_48ac7dda_uniq` (`backupschedule_id`,`customuser_id`),
  KEY `notificationApp_back_customuser_id_0dea04f9_fk_accounts_` (`customuser_id`),
  CONSTRAINT `notificationApp_back_backupschedule_id_4390550e_fk_notificat` FOREIGN KEY (`backupschedule_id`) REFERENCES `notificationApp_backupschedule` (`id`),
  CONSTRAINT `notificationApp_back_customuser_id_0dea04f9_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_notification`
--

DROP TABLE IF EXISTS `notificationApp_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_notification` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `verb` varchar(100) NOT NULL,
  `description` longtext,
  `unread` tinyint(1) NOT NULL,
  `deleted` tinyint(1) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `entity_type` varchar(50) NOT NULL,
  `target_object_id` int unsigned DEFAULT NULL,
  `actor_id` bigint DEFAULT NULL,
  `recipient_id` bigint NOT NULL,
  `target_content_type_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `notificationApp_noti_actor_id_b13c13c5_fk_accounts_` (`actor_id`),
  KEY `notificationApp_noti_recipient_id_5f46c8a3_fk_accounts_` (`recipient_id`),
  KEY `notificationApp_noti_target_content_type__c3ec6fd6_fk_django_co` (`target_content_type_id`),
  CONSTRAINT `notificationApp_noti_actor_id_b13c13c5_fk_accounts_` FOREIGN KEY (`actor_id`) REFERENCES `accounts_customuser` (`id`),
  CONSTRAINT `notificationApp_noti_recipient_id_5f46c8a3_fk_accounts_` FOREIGN KEY (`recipient_id`) REFERENCES `accounts_customuser` (`id`),
  CONSTRAINT `notificationApp_noti_target_content_type__c3ec6fd6_fk_django_co` FOREIGN KEY (`target_content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `notificationApp_notification_chk_1` CHECK ((`target_object_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_notificationrule`
--

DROP TABLE IF EXISTS `notificationApp_notificationrule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_notificationrule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(50) NOT NULL,
  `action` varchar(50) NOT NULL,
  `priority` varchar(20) NOT NULL,
  `channel` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationApp_notificationrule_recipients`
--

DROP TABLE IF EXISTS `notificationApp_notificationrule_recipients`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationApp_notificationrule_recipients` (
  `id` int NOT NULL AUTO_INCREMENT,
  `notificationrule_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `notificationApp_notifica_notificationrule_id_post_ee1e8aa8_uniq` (`notificationrule_id`,`post_id`),
  KEY `notificationApp_noti_post_id_6348887d_fk_core_post` (`post_id`),
  CONSTRAINT `notificationApp_noti_notificationrule_id_fe2eb4af_fk_notificat` FOREIGN KEY (`notificationrule_id`) REFERENCES `notificationApp_notificationrule` (`id`),
  CONSTRAINT `notificationApp_noti_post_id_6348887d_fk_core_post` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notificationapp_notificationrule`
--

DROP TABLE IF EXISTS `notificationapp_notificationrule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notificationapp_notificationrule` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `priority` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `channel` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notifications_notification`
--

DROP TABLE IF EXISTS `notifications_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications_notification` (
  `id` int NOT NULL AUTO_INCREMENT,
  `level` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `unread` tinyint(1) NOT NULL,
  `actor_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `verb` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `target_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `action_object_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `public` tinyint(1) NOT NULL,
  `deleted` tinyint(1) NOT NULL,
  `emailed` tinyint(1) NOT NULL,
  `data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `action_object_content_type_id` int DEFAULT NULL,
  `actor_content_type_id` int NOT NULL,
  `recipient_id` bigint NOT NULL,
  `target_content_type_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `notifications_notifi_action_object_conten_7d2b8ee9_fk_django_co` (`action_object_content_type_id`) USING BTREE,
  KEY `notifications_notifi_actor_content_type_i_0c69d7b7_fk_django_co` (`actor_content_type_id`) USING BTREE,
  KEY `notifications_notifi_recipient_id_d055f3f0_fk_accounts_` (`recipient_id`) USING BTREE,
  KEY `notifications_notifi_target_content_type__ccb24d88_fk_django_co` (`target_content_type_id`) USING BTREE,
  KEY `notifications_notification_unread_cce4be30` (`unread`) USING BTREE,
  KEY `notifications_notification_timestamp_6a797bad` (`timestamp`) USING BTREE,
  KEY `notifications_notification_public_1bc30b1c` (`public`) USING BTREE,
  KEY `notifications_notification_deleted_b32b69e6` (`deleted`) USING BTREE,
  KEY `notifications_notification_emailed_23a5ad81` (`emailed`) USING BTREE,
  CONSTRAINT `notifications_notifi_action_object_conten_7d2b8ee9_fk_django_co` FOREIGN KEY (`action_object_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_actor_content_type_i_0c69d7b7_fk_django_co` FOREIGN KEY (`actor_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_recipient_id_d055f3f0_fk_accounts_` FOREIGN KEY (`recipient_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_target_content_type__ccb24d88_fk_django_co` FOREIGN KEY (`target_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `purchase_requests_purchaserequest`
--

DROP TABLE IF EXISTS `purchase_requests_purchaserequest`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_requests_purchaserequest` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `date` date NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `project_id` bigint DEFAULT NULL,
  `status_id` bigint DEFAULT NULL,
  `subproject_id` bigint DEFAULT NULL,
  `external_id` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `external_payload` json DEFAULT NULL,
  `is_synced` tinyint(1) NOT NULL,
  `source_system` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `synced_at` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `number` (`number`) USING BTREE,
  KEY `purchase_requests_pu_created_by_id_34412446_fk_accounts_` (`created_by_id`) USING BTREE,
  KEY `purchase_requests_pu_project_id_240fc284_fk_core_proj` (`project_id`) USING BTREE,
  KEY `purchase_requests_pu_status_id_d5be6761_fk_core_stat` (`status_id`) USING BTREE,
  KEY `purchase_requests_pu_subproject_id_5f0583cc_fk_core_subp` (`subproject_id`) USING BTREE,
  KEY `purchase_re_number_6001f3_idx` (`number`) USING BTREE,
  KEY `purchase_re_organiz_fbb6d0_idx` (`organization_id`,`date`) USING BTREE,
  KEY `purchase_re_source__d17c02_idx` (`source_system`,`external_id`) USING BTREE,
  CONSTRAINT `purchase_requests_pu_created_by_id_34412446_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_organization_id_f2200998_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_project_id_240fc284_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_status_id_d5be6761_fk_core_stat` FOREIGN KEY (`status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_subproject_id_5f0583cc_fk_core_subp` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `purchase_requests_purchaserequestitem`
--

DROP TABLE IF EXISTS `purchase_requests_purchaserequestitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `purchase_requests_purchaserequestitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `quantity` decimal(25,2) NOT NULL,
  `unit_price` decimal(25,2) NOT NULL,
  `amount` decimal(25,2) NOT NULL,
  `request_id` bigint NOT NULL,
  `external_item_id` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `sku` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `uom` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `purchase_re_request_c03fee_idx` (`request_id`) USING BTREE,
  KEY `purchase_re_sku_414960_idx` (`sku`) USING BTREE,
  CONSTRAINT `purchase_requests_pu_request_id_d410aad4_fk_purchase_` FOREIGN KEY (`request_id`) REFERENCES `purchase_requests_purchaserequest` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_financialreport`
--

DROP TABLE IF EXISTS `reports_financialreport`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_financialreport` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `total_amount` decimal(25,2) NOT NULL,
  `approved_amount` decimal(25,2) NOT NULL,
  `rejected_amount` decimal(25,2) NOT NULL,
  `payment_number` varchar(50) DEFAULT NULL,
  `report_date` datetime(6) NOT NULL,
  `last_status` varchar(20) DEFAULT NULL,
  `total_factors` int NOT NULL,
  `approved_factors` int NOT NULL,
  `rejected_factors` int NOT NULL,
  `tankhah_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tankhah_id` (`tankhah_id`),
  CONSTRAINT `reports_financialrep_tankhah_id_fbe00afd_fk_tankhah_t` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_print_financial_report`
--

DROP TABLE IF EXISTS `reports_print_financial_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_print_financial_report` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_reportsapis`
--

DROP TABLE IF EXISTS `reports_reportsapis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_reportsapis` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_reportsdashboard`
--

DROP TABLE IF EXISTS `reports_reportsdashboard`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_reportsdashboard` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_send_to_accounting`
--

DROP TABLE IF EXISTS `reports_send_to_accounting`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_send_to_accounting` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_tankhah_financialreport`
--

DROP TABLE IF EXISTS `reports_tankhah_financialreport`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_tankhah_financialreport` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reports_tankhahdetailview`
--

DROP TABLE IF EXISTS `reports_tankhahdetailview`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `reports_tankhahdetailview` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_approvallog`
--

DROP TABLE IF EXISTS `tankhah_approvallog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_approvallog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `timestamp` datetime(6) NOT NULL,
  `changed_field` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `seen_by_higher` tinyint(1) NOT NULL,
  `seen_at` datetime(6) DEFAULT NULL,
  `post_id` bigint DEFAULT NULL,
  `stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  `factor_id` bigint DEFAULT NULL,
  `factor_item_id` bigint DEFAULT NULL,
  `tankhah_id` bigint DEFAULT NULL,
  `content_type_id` int DEFAULT NULL,
  `object_id` int unsigned NOT NULL,
  `is_final_approval` tinyint(1) NOT NULL,
  `stage_order` int unsigned DEFAULT NULL,
  `stage_id` int DEFAULT NULL,
  `is_temporary` tinyint DEFAULT NULL,
  `stage_rule_id` bigint DEFAULT NULL,
  `from_status_id` bigint NOT NULL,
  `to_status_id` bigint DEFAULT NULL,
  `action_id` bigint DEFAULT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_admin_action` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_approvallog_post_id_25bdf3fb_fk_core_post_id` (`post_id`) USING BTREE,
  KEY `tankhah_approvallog_user_id_90f106ab_fk_accounts_customuser_id` (`user_id`) USING BTREE,
  KEY `tankhah_approvallog_factor_id_37f79ad1_fk_tankhah_factor_id` (`factor_id`) USING BTREE,
  KEY `tankhah_approvallog_factor_item_id_34ec4a58_fk_tankhah_f` (`factor_item_id`) USING BTREE,
  KEY `tankhah_approvallog_tankhah_id_e5d39b2f_fk_tankhah_tankhah_id` (`tankhah_id`) USING BTREE,
  KEY `tankhah_approvallog_content_type_id_2fb149e4_fk_django_co` (`content_type_id`) USING BTREE,
  KEY `tankhah_app_factor__add5d7_idx` (`factor_id`,`tankhah_id`,`user_id`,`stage`) USING BTREE,
  KEY `tankhah_approvallog_from_status_id_3559100a_fk_core_status_id` (`from_status_id`) USING BTREE,
  KEY `tankhah_approvallog_stage_rule_id_c3925304_fk_core_status_id` (`stage_rule_id`) USING BTREE,
  KEY `tankhah_approvallog_created_by_id_033c0640_fk_accounts_` (`created_by_id`) USING BTREE,
  CONSTRAINT `tankhah_approvallog_content_type_id_2fb149e4_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_created_by_id_033c0640_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_factor_id_37f79ad1_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_factor_item_id_34ec4a58_fk_tankhah_f` FOREIGN KEY (`factor_item_id`) REFERENCES `tankhah_factoritem` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_from_status_id_3559100a_fk_core_status_id` FOREIGN KEY (`from_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_post_id_25bdf3fb_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_stage_rule_id_c3925304_fk_core_status_id` FOREIGN KEY (`stage_rule_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_tankhah_id_e5d39b2f_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_user_id_90f106ab_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_chk_1` CHECK ((`object_id` >= 0)),
  CONSTRAINT `tankhah_approvallog_chk_2` CHECK ((`stage_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=342 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_dashboard_tankhah`
--

DROP TABLE IF EXISTS `tankhah_dashboard_tankhah`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_dashboard_tankhah` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_factor`
--

DROP TABLE IF EXISTS `tankhah_factor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_factor` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `date` date NOT NULL,
  `amount` decimal(20,2) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `status_id` bigint DEFAULT NULL,
  `locked_by_stage_id` bigint DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  `budget` decimal(20,2) NOT NULL,
  `remaining_budget` decimal(20,2) NOT NULL,
  `created_by_id` bigint NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_emergency` tinyint(1) NOT NULL,
  `category_id` bigint NOT NULL,
  `is_locked` tinyint(1) DEFAULT '0',
  `re_registered_in_id` bigint DEFAULT NULL,
  `rejected_reason` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `deleted_at` datetime(6) DEFAULT NULL,
  `deleted_by_id` bigint DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `payee_id` bigint DEFAULT NULL,
  `archived_at` datetime(6) DEFAULT NULL,
  `archived_by_id` bigint DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `purchase_request_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_factor_tankhah_id_b1fd1df3_fk_tankhah_tankhah_id` (`tankhah_id`) USING BTREE,
  KEY `tankhah_factor_locked_by_stage_id_a274da7d_fk_core_work` (`locked_by_stage_id`) USING BTREE,
  KEY `tankhah_factor_created_by_id_b06575df_fk_accounts_customuser_id` (`created_by_id`) USING BTREE,
  KEY `tankhah_factor_category_id_4e863d6f_fk_tankhah_itemcategory_id` (`category_id`) USING BTREE,
  KEY `tankhah_factor_re_registered_in_id_a27b90b0_fk_tankhah_t` (`re_registered_in_id`) USING BTREE,
  KEY `tankhah_factor_deleted_by_id_877ae561_fk_accounts_customuser_id` (`deleted_by_id`) USING BTREE,
  KEY `tankhah_factor_status_id_fk_core_status_id` (`status_id`) USING BTREE,
  KEY `tankhah_factor_archived_by_id_785e6d61_fk_accounts_customuser_id` (`archived_by_id`) USING BTREE,
  KEY `tankhah_factor_purchase_request_id_d703a494_fk_purchase_` (`purchase_request_id`) USING BTREE,
  CONSTRAINT `tankhah_factor_archived_by_id_785e6d61_fk_accounts_customuser_id` FOREIGN KEY (`archived_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_category_id_4e863d6f_fk_tankhah_itemcategory_id` FOREIGN KEY (`category_id`) REFERENCES `tankhah_itemcategory` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_created_by_id_b06575df_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_deleted_by_id_877ae561_fk_accounts_customuser_id` FOREIGN KEY (`deleted_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_locked_by_stage_id_a274da7d_fk_core_status_id` FOREIGN KEY (`locked_by_stage_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_purchase_request_id_d703a494_fk_purchase_` FOREIGN KEY (`purchase_request_id`) REFERENCES `purchase_requests_purchaserequest` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_re_registered_in_id_a27b90b0_fk_tankhah_t` FOREIGN KEY (`re_registered_in_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_status_id_fk_core_status_id` FOREIGN KEY (`status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_tankhah_id_b1fd1df3_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=89 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_factordocument`
--

DROP TABLE IF EXISTS `tankhah_factordocument`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_factordocument` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `file_size` int DEFAULT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `factor_id` bigint NOT NULL,
  `uploaded_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_factordocument_factor_id_5f2b8fc0_fk_tankhah_factor_id` (`factor_id`) USING BTREE,
  KEY `tankhah_factordocume_uploaded_by_id_efc84e28_fk_accounts_` (`uploaded_by_id`) USING BTREE,
  CONSTRAINT `tankhah_factordocume_uploaded_by_id_efc84e28_fk_accounts_` FOREIGN KEY (`uploaded_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factordocument_factor_id_5f2b8fc0_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_factorhistory`
--

DROP TABLE IF EXISTS `tankhah_factorhistory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_factorhistory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `change_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `change_timestamp` datetime(6) NOT NULL,
  `old_data` json DEFAULT NULL,
  `new_data` json DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `changed_by_id` bigint DEFAULT NULL,
  `factor_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_factorhistor_changed_by_id_29dcfeeb_fk_accounts_` (`changed_by_id`) USING BTREE,
  KEY `tankhah_factorhistory_factor_id_5bd16d12_fk_tankhah_factor_id` (`factor_id`) USING BTREE,
  CONSTRAINT `tankhah_factorhistor_changed_by_id_29dcfeeb_fk_accounts_` FOREIGN KEY (`changed_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factorhistory_factor_id_5bd16d12_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=1919 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_factoritem`
--

DROP TABLE IF EXISTS `tankhah_factoritem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_factoritem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25,2) NOT NULL,
  `status_id` bigint DEFAULT NULL,
  `quantity` decimal(25,2) NOT NULL,
  `unit_price` decimal(25,1) NOT NULL,
  `factor_id` bigint NOT NULL,
  `min_stage_order` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_factoritem_factor_id_2bb74929_fk_tankhah_factor_id` (`factor_id`) USING BTREE,
  CONSTRAINT `tankhah_factoritem_factor_id_2bb74929_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=111 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_itemcategory`
--

DROP TABLE IF EXISTS `tankhah_itemcategory`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_itemcategory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `min_stage_order` int NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_stageapprover`
--

DROP TABLE IF EXISTS `tankhah_stageapprover`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_stageapprover` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_active` tinyint(1) NOT NULL,
  `post_id` bigint NOT NULL,
  `stage_id` bigint NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `organization_id` bigint NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `tankhah_stageapprover_stage_id_post_id_entity__9b6c6913_uniq` (`stage_id`,`post_id`,`entity_type`,`organization_id`) USING BTREE,
  KEY `tankhah_stageapprover_post_id_1d6b0b80` (`post_id`) USING BTREE,
  KEY `tankhah_stageapprover_stage_id_d82b75e0` (`stage_id`) USING BTREE,
  KEY `tankhah_stageapprove_organization_id_3ea4ea52_fk_core_orga` (`organization_id`) USING BTREE,
  CONSTRAINT `tankhah_stageapprove_organization_id_3ea4ea52_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_stageapprover_post_id_1d6b0b80_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhactiontype`
--

DROP TABLE IF EXISTS `tankhah_tankhactiontype`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhactiontype` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action_type` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `code` (`code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhah`
--

DROP TABLE IF EXISTS `tankhah_tankhah`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhah` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25,2) NOT NULL,
  `date` datetime(6) NOT NULL,
  `due_date` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `letter_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status_id` bigint NOT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `payment_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  `archived_at` datetime(6) DEFAULT NULL,
  `canceled` tinyint(1) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `last_stopped_post_id` bigint DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `project_id` bigint DEFAULT NULL,
  `subproject_id` bigint DEFAULT NULL,
  `remaining_budget` decimal(25,2) NOT NULL,
  `budget_allocation_id` bigint DEFAULT NULL,
  `is_emergency` tinyint(1) NOT NULL,
  `request_date` date NOT NULL,
  `project_budget_allocation_id` bigint DEFAULT NULL,
  `payment_ceiling` decimal(10,0) DEFAULT NULL,
  `is_payment_ceiling_enabled` tinyint(1) DEFAULT '0',
  `current_stage_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `number` (`number`) USING BTREE,
  KEY `tankhah_tan_number_dd4c50_idx` (`number`,`date`,`status_id`,`organization_id`) USING BTREE,
  KEY `tankhah_tankhah_created_by_id_b29865c0_fk_accounts_customuser_id` (`created_by_id`) USING BTREE,
  KEY `tankhah_tankhah_last_stopped_post_id_7592e558_fk_core_post_id` (`last_stopped_post_id`) USING BTREE,
  KEY `tankhah_tankhah_organization_id_01642aa9_fk_core_organization_id` (`organization_id`) USING BTREE,
  KEY `tankhah_tankhah_project_id_54b0b7e7_fk_core_project_id` (`project_id`) USING BTREE,
  KEY `tankhah_tankhah_subproject_id_d314449d_fk_core_subproject_id` (`subproject_id`) USING BTREE,
  KEY `tankhah_tankhah_budget_allocation_id_25455474_fk_budgets_b` (`budget_allocation_id`) USING BTREE,
  KEY `tankhah_tankhah_project_budget_alloc_5eeaa99b_fk_budgets_p` (`project_budget_allocation_id`) USING BTREE,
  KEY `tankhah_tankhah_current_stage_id_e5890193_fk_core_status_id` (`current_stage_id`) USING BTREE,
  KEY `tankhah_tan_number_ddd2e8_idx` (`number`,`date`,`status_id`,`organization_id`,`project_id`,`created_at`) USING BTREE,
  CONSTRAINT `tankhah_tankhah_budget_allocation_id_25455474_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_created_by_id_b29865c0_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_current_stage_id_e5890193_fk_core_status_id` FOREIGN KEY (`current_stage_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_last_stopped_post_id_7592e558_fk_core_post_id` FOREIGN KEY (`last_stopped_post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_organization_id_01642aa9_fk_core_organization_id` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_project_id_54b0b7e7_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_subproject_id_d314449d_fk_core_subproject_id` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhah_approved_by`
--

DROP TABLE IF EXISTS `tankhah_tankhah_approved_by`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhah_approved_by` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tankhah_id` bigint NOT NULL,
  `customuser_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `tankhah_tankhah_approved_tankhah_id_customuser_id_46225e0c_uniq` (`tankhah_id`,`customuser_id`) USING BTREE,
  KEY `tankhah_tankhah_appr_customuser_id_8ddccd3b_fk_accounts_` (`customuser_id`) USING BTREE,
  CONSTRAINT `tankhah_tankhah_appr_customuser_id_8ddccd3b_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_appr_tankhah_id_1877bab9_fk_tankhah_t` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhahaction`
--

DROP TABLE IF EXISTS `tankhah_tankhahaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhahaction` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tankhah_id` bigint NOT NULL,
  `amount` decimal(25,2) DEFAULT NULL,
  `stage_id` bigint NOT NULL,
  `post_id` bigint DEFAULT NULL,
  `user_id` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `reference_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT '',
  `action_type_id` bigint DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_action_tankhah_fk` (`tankhah_id`) USING BTREE,
  KEY `tankhah_action_stage_fk` (`stage_id`) USING BTREE,
  KEY `tankhah_action_post_fk` (`post_id`) USING BTREE,
  KEY `tankhah_action_user_fk` (`user_id`) USING BTREE,
  KEY `tankhah_action_actiontype_fk` (`action_type_id`) USING BTREE,
  CONSTRAINT `tankhah_action_actiontype_fk` FOREIGN KEY (`action_type_id`) REFERENCES `budgets_transactiontype` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_post_fk` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_stage_fk` FOREIGN KEY (`stage_id`) REFERENCES `core_workflowstage` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_tankhah_fk` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_user_fk` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhahdocument`
--

DROP TABLE IF EXISTS `tankhah_tankhahdocument`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhahdocument` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `file_size` int DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `tankhah_tankhahdocum_tankhah_id_a34f34d7_fk_tankhah_t` (`tankhah_id`) USING BTREE,
  CONSTRAINT `tankhah_tankhahdocum_tankhah_id_a34f34d7_fk_tankhah_t` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tankhah_tankhahfinalapproval`
--

DROP TABLE IF EXISTS `tankhah_tankhahfinalapproval`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tankhah_tankhahfinalapproval` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_appversion`
--

DROP TABLE IF EXISTS `version_tracker_appversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_appversion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `version_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `version_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `release_date` datetime(6) NOT NULL,
  `code_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `changed_files` json NOT NULL,
  `system_info` json NOT NULL,
  `author_id` bigint NOT NULL,
  `major` int unsigned NOT NULL DEFAULT '0',
  `minor` int unsigned NOT NULL DEFAULT '0',
  `patch` int unsigned NOT NULL DEFAULT '0',
  `build` int unsigned NOT NULL DEFAULT '0',
  `previous_version_id` bigint DEFAULT NULL,
  `is_final` tinyint(1) NOT NULL DEFAULT '0',
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `unique_version` (`app_name`,`major`,`minor`,`patch`,`build`) USING BTREE,
  KEY `idx_app_name` (`app_name`) USING BTREE,
  KEY `idx_version_number` (`version_number`) USING BTREE,
  KEY `idx_release_date` (`release_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2727 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_backuplocation`
--

DROP TABLE IF EXISTS `version_tracker_backuplocation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_backuplocation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `location_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `is_encrypted` tinyint(1) NOT NULL,
  `max_size_gb` int DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `created_at` datetime(6) NOT NULL,
  `last_tested` datetime(6) DEFAULT NULL,
  `last_error` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `created_by_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `version_tracker_back_created_by_id_c55eccd4_fk_accounts_` (`created_by_id`) USING BTREE,
  CONSTRAINT `version_tracker_back_created_by_id_c55eccd4_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_codechangelog`
--

DROP TABLE IF EXISTS `version_tracker_codechangelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_codechangelog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_id` bigint NOT NULL,
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `change_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'modified',
  `change_date` datetime(6) NOT NULL,
  `old_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `new_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `unique_version_file` (`version_id`,`file_name`) USING BTREE,
  KEY `idx_version` (`version_id`) USING BTREE,
  KEY `idx_change_date` (`change_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=33419 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_filehash`
--

DROP TABLE IF EXISTS `version_tracker_filehash`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_filehash` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app_version_id` bigint NOT NULL,
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `hash_value` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `unique_file_version` (`app_version_id`,`file_path`) USING BTREE,
  KEY `idx_app_version` (`app_version_id`) USING BTREE,
  KEY `idx_timestamp` (`timestamp`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=109962 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_finalversion`
--

DROP TABLE IF EXISTS `version_tracker_finalversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_finalversion` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_number` varchar(20) NOT NULL,
  `release_date` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `version_tracker_finalversion_release_date_c20ebe81` (`release_date`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `version_tracker_finalversion_app_versions`
--

DROP TABLE IF EXISTS `version_tracker_finalversion_app_versions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_tracker_finalversion_app_versions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `finalversion_id` bigint NOT NULL,
  `appversion_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `version_tracker_finalver_finalversion_id_appversi_e7a4bca7_uniq` (`finalversion_id`,`appversion_id`),
  KEY `version_tracker_fina_appversion_id_8323129b_fk_version_t` (`appversion_id`),
  CONSTRAINT `version_tracker_fina_appversion_id_8323129b_fk_version_t` FOREIGN KEY (`appversion_id`) REFERENCES `version_tracker_appversion` (`id`),
  CONSTRAINT `version_tracker_fina_finalversion_id_65306579_fk_version_t` FOREIGN KEY (`finalversion_id`) REFERENCES `version_tracker_finalversion` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=183 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-25 18:47:51
