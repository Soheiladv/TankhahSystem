/*
 Navicat Premium Dump SQL

 Source Server         : localhost_3306
 Source Server Type    : MySQL
 Source Server Version : 80031 (8.0.31)
 Source Host           : localhost:3306
 Source Schema         : tankhasystem

 Target Server Type    : MySQL
 Target Server Version : 80031 (8.0.31)
 File Encoding         : 65001

 Date: 26/11/2025 10:42:32
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for accounts_activeuser
-- ----------------------------
DROP TABLE IF EXISTS `accounts_activeuser`;
CREATE TABLE `accounts_activeuser`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `login_time` datetime(6) NOT NULL,
  `hashed_count` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `last_activity` datetime(6) NOT NULL,
  `user_ip` char(39) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `user_agent` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `logout_time` datetime(6) NULL DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_user_session`(`user_id` ASC) USING BTREE,
  INDEX `accounts_activeuser_session_key_48b1d026`(`session_key` ASC) USING BTREE,
  INDEX `accounts_activeuser_login_time_3b4e1b1e`(`login_time` ASC) USING BTREE,
  INDEX `accounts_activeuser_last_activity_493e764f`(`last_activity` ASC) USING BTREE,
  INDEX `idx_user`(`user_id` ASC) USING BTREE,
  INDEX `idx_last_activity`(`last_activity` ASC) USING BTREE,
  CONSTRAINT `accounts_activeuser_user_id_43ede48b_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `check_login_before_activity` CHECK (`login_time` <= `last_activity`)
) ENGINE = InnoDB AUTO_INCREMENT = 212 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_audit_log
-- ----------------------------
DROP TABLE IF EXISTS `accounts_audit_log`;
CREATE TABLE `accounts_audit_log`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `view_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `method` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `model_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `changes` json NULL,
  `ip_address` char(39) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `browser` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status_code` int NULL DEFAULT NULL,
  `related_object` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `accounts_audit_log_user_id_92f0051c_fk_accounts_customuser_id`(`user_id` ASC) USING BTREE,
  CONSTRAINT `accounts_audit_log_user_id_92f0051c_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 21318 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_city
-- ----------------------------
DROP TABLE IF EXISTS `accounts_city`;
CREATE TABLE `accounts_city`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_capital` tinyint(1) NOT NULL,
  `province_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_city_name_province_id_0f905959_uniq`(`name` ASC, `province_id` ASC) USING BTREE,
  INDEX `accounts_city_province_id_3c87e1c3_fk_accounts_province_id`(`province_id` ASC) USING BTREE,
  CONSTRAINT `accounts_city_province_id_3c87e1c3_fk_accounts_province_id` FOREIGN KEY (`province_id`) REFERENCES `accounts_province` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_customprofile
-- ----------------------------
DROP TABLE IF EXISTS `accounts_customprofile`;
CREATE TABLE `accounts_customprofile`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `first_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `phone_number` varchar(15) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `birth_date` date NULL DEFAULT NULL,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `location` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `bio` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `zip_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `theme` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `city_id` bigint NULL DEFAULT NULL,
  `user_id` bigint NOT NULL,
  `province_id` bigint NULL DEFAULT NULL,
  `custom_theme_data` json NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `user_id`(`user_id` ASC) USING BTREE,
  INDEX `accounts_customprofile_city_id_e241f232_fk_accounts_city_id`(`city_id` ASC) USING BTREE,
  INDEX `accounts_customprofi_province_id_76bdd0ef_fk_accounts_`(`province_id` ASC) USING BTREE,
  CONSTRAINT `accounts_customprofi_province_id_76bdd0ef_fk_accounts_` FOREIGN KEY (`province_id`) REFERENCES `accounts_province` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customprofi_user_id_150416de_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customprofile_city_id_e241f232_fk_accounts_city_id` FOREIGN KEY (`city_id`) REFERENCES `accounts_city` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 11 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_customuser
-- ----------------------------
DROP TABLE IF EXISTS `accounts_customuser`;
CREATE TABLE `accounts_customuser`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_login` datetime(6) NULL DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `email` varchar(254) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `first_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `last_name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `username`(`username` ASC) USING BTREE,
  UNIQUE INDEX `email`(`email` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 50 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_customuser_groups
-- ----------------------------
DROP TABLE IF EXISTS `accounts_customuser_groups`;
CREATE TABLE `accounts_customuser_groups`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `mygroup_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `accounts_customuser__customuser_id_bc55088e_fk_accounts_`(`customuser_id` ASC) USING BTREE,
  INDEX `accounts_customuser__mygroup_id_e98a3018_fk_accounts_`(`mygroup_id` ASC) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_bc55088e_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser__mygroup_id_e98a3018_fk_accounts_` FOREIGN KEY (`mygroup_id`) REFERENCES `accounts_mygroups` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 37 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_customuser_roles
-- ----------------------------
DROP TABLE IF EXISTS `accounts_customuser_roles`;
CREATE TABLE `accounts_customuser_roles`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_customuser_roles_customuser_id_role_id_4c344b94_uniq`(`customuser_id` ASC, `role_id` ASC) USING BTREE,
  INDEX `accounts_customuser_roles_role_id_e0ee129a_fk_accounts_role_id`(`role_id` ASC) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_737b4b7e_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser_roles_role_id_e0ee129a_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 8 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_customuser_user_permissions
-- ----------------------------
DROP TABLE IF EXISTS `accounts_customuser_user_permissions`;
CREATE TABLE `accounts_customuser_user_permissions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `customuser_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_customuser_user_customuser_id_permission_9632a709_uniq`(`customuser_id` ASC, `permission_id` ASC) USING BTREE,
  INDEX `accounts_customuser__permission_id_aea3d0e5_fk_auth_perm`(`permission_id` ASC) USING BTREE,
  CONSTRAINT `accounts_customuser__customuser_id_0deaefae_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_customuser__permission_id_aea3d0e5_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 455 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_mygroups
-- ----------------------------
DROP TABLE IF EXISTS `accounts_mygroups`;
CREATE TABLE `accounts_mygroups`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 11 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_mygroups_roles
-- ----------------------------
DROP TABLE IF EXISTS `accounts_mygroups_roles`;
CREATE TABLE `accounts_mygroups_roles`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `mygroup_id` bigint NOT NULL,
  `role_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_mygroups_roles_mygroup_id_role_id_fd84a847_uniq`(`mygroup_id` ASC, `role_id` ASC) USING BTREE,
  INDEX `accounts_mygroups_roles_role_id_6c64e294_fk_accounts_role_id`(`role_id` ASC) USING BTREE,
  CONSTRAINT `accounts_mygroups_ro_mygroup_id_0e3dee22_fk_accounts_` FOREIGN KEY (`mygroup_id`) REFERENCES `accounts_mygroups` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_mygroups_roles_role_id_6c64e294_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_province
-- ----------------------------
DROP TABLE IF EXISTS `accounts_province`;
CREATE TABLE `accounts_province`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(2) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_role
-- ----------------------------
DROP TABLE IF EXISTS `accounts_role`;
CREATE TABLE `accounts_role`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `parent_id` bigint NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `accounts_role_parent_id_526243b4_fk_accounts_role_id`(`parent_id` ASC) USING BTREE,
  CONSTRAINT `accounts_role_parent_id_526243b4_fk_accounts_role_id` FOREIGN KEY (`parent_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 12 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_role_permissions
-- ----------------------------
DROP TABLE IF EXISTS `accounts_role_permissions`;
CREATE TABLE `accounts_role_permissions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `accounts_role_permissions_role_id_permission_id_032c715e_uniq`(`role_id` ASC, `permission_id` ASC) USING BTREE,
  INDEX `accounts_role_permis_permission_id_76fe677d_fk_auth_perm`(`permission_id` ASC) USING BTREE,
  CONSTRAINT `accounts_role_permis_permission_id_76fe677d_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `accounts_role_permissions_role_id_54f107a6_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 2186 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for accounts_timelockmodel
-- ----------------------------
DROP TABLE IF EXISTS `accounts_timelockmodel`;
CREATE TABLE `accounts_timelockmodel`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `lock_key` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `hash_value` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `salt` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `organization_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `hash_value`(`hash_value` ASC) USING BTREE,
  UNIQUE INDEX `salt`(`salt` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for admin_interface_theme
-- ----------------------------
DROP TABLE IF EXISTS `admin_interface_theme`;
CREATE TABLE `admin_interface_theme`  (
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
  `logo_max_height` smallint UNSIGNED NOT NULL,
  `logo_max_width` smallint UNSIGNED NOT NULL,
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
  UNIQUE INDEX `admin_interface_theme_name_30bda70f_uniq`(`name` ASC) USING BTREE,
  CONSTRAINT `admin_interface_theme_chk_1` CHECK (`logo_max_height` >= 0),
  CONSTRAINT `admin_interface_theme_chk_2` CHECK (`logo_max_width` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for auth_group
-- ----------------------------
DROP TABLE IF EXISTS `auth_group`;
CREATE TABLE `auth_group`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for auth_group_permissions
-- ----------------------------
DROP TABLE IF EXISTS `auth_group_permissions`;
CREATE TABLE `auth_group_permissions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `auth_group_permissions_group_id_permission_id_0cd325b0_uniq`(`group_id` ASC, `permission_id` ASC) USING BTREE,
  INDEX `auth_group_permissions_permission_id_84c5c92e_fk`(`permission_id` ASC) USING BTREE,
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `auth_group_permissions_permission_id_84c5c92e_fk` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for auth_permission
-- ----------------------------
DROP TABLE IF EXISTS `auth_permission`;
CREATE TABLE `auth_permission`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `auth_permission_content_type_id_codename_01ab375a_uniq`(`content_type_id` ASC, `codename` ASC) USING BTREE,
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 377 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgetallocation
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgetallocation`;
CREATE TABLE `budgets_budgetallocation`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `allocated_amount` decimal(25, 2) NOT NULL,
  `allocation_date` date NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `budget_period_id` bigint NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `project_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `allocation_number` int NOT NULL,
  `is_stopped` tinyint(1) NOT NULL,
  `locked_percentage` decimal(5, 2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `warning_threshold` decimal(5, 2) NOT NULL,
  `returned_amount` decimal(25, 2) NOT NULL,
  `budget_item_id` bigint NULL DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  `subproject_id` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `budgets_budgetalloca_created_by_id_8203e930_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `budgets_bud_budget__3d5534_idx`(`budget_period_id` ASC, `allocation_date` ASC) USING BTREE,
  INDEX `budgets_bud_organiz_05ceb0_idx`(`organization_id` ASC, `allocated_amount` ASC) USING BTREE,
  INDEX `budgets_budgetallocation_project_id_d67ab494_fk_core_project_id`(`project_id` ASC) USING BTREE,
  CONSTRAINT `budgets_budgetalloca_budget_period_id_08592985_fk_budgets_b` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetalloca_created_by_id_8203e930_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetalloca_organization_id_3b329857_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetallocation_project_id_d67ab494_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 98 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgethistory
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgethistory`;
CREATE TABLE `budgets_budgethistory`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` int UNSIGNED NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25, 2) NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `transaction_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `content_type_id` int NOT NULL,
  `transaction_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `transaction_id`(`transaction_id` ASC) USING BTREE,
  INDEX `budgets_budgethistor_created_by_id_c66a36b4_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `budgets_budgethistor_content_type_id_2a837fe7_fk_django_co`(`content_type_id` ASC) USING BTREE,
  CONSTRAINT `budgets_budgethistor_content_type_id_2a837fe7_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgethistor_created_by_id_c66a36b4_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgethistory_chk_1` CHECK (`object_id` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 72 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgetitem
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgetitem`;
CREATE TABLE `budgets_budgetitem`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `budget_period_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `create_at` datetime(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE,
  UNIQUE INDEX `uq_budgetitem_period_org_code`(`budget_period_id` ASC, `organization_id` ASC, `code` ASC) USING BTREE,
  INDEX `fk_budgetitem_organization`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `fk_budgetitem_budgetperiod` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `fk_budgetitem_organization` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 24 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgetperiod
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgetperiod`;
CREATE TABLE `budgets_budgetperiod`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `total_amount` decimal(25, 0) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `lock_condition` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `locked_percentage` int NOT NULL,
  `warning_threshold` decimal(5, 2) NOT NULL,
  `is_completed` tinyint(1) NOT NULL,
  `total_allocated` decimal(25, 2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_phase` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `returned_amount` decimal(25, 2) NOT NULL,
  `is_period_locked` tinyint(1) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `budgets_budgetperiod_name_01bedea2_uniq`(`name` ASC) USING BTREE,
  INDEX `IX_BudgetPeriod_organization_id`(`organization_id` ASC) USING BTREE,
  INDEX `IX_BudgetPeriod_created_by_id`(`created_by_id` ASC) USING BTREE,
  INDEX `IX_BudgetPeriod_Dates`(`start_date` ASC, `end_date` ASC) USING BTREE,
  CONSTRAINT `budgets_budgetperiod_created_by_id_487cfefd_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetperiod_organization_id_fa17309e_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 32 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgetreallocation
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgetreallocation`;
CREATE TABLE `budgets_budgetreallocation`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `amount` decimal(25, 2) NOT NULL,
  `reallocation_date` date NOT NULL,
  `reason` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `source_allocation_id` bigint NOT NULL,
  `target_allocation_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `budgets_budgetreallo_source_allocation_id_d454eec2_fk_budgets_b`(`source_allocation_id` ASC) USING BTREE,
  INDEX `budgets_budgetreallo_target_allocation_id_e57b016e_fk_budgets_b`(`target_allocation_id` ASC) USING BTREE,
  INDEX `budgets_budgetreallo_created_by_id_931b064f_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `budgets_budgetreallo_created_by_id_931b064f_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetreallo_source_allocation_id_d454eec2_fk_budgets_b` FOREIGN KEY (`source_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetreallo_target_allocation_id_e57b016e_fk_budgets_b` FOREIGN KEY (`target_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgetsettings
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgetsettings`;
CREATE TABLE `budgets_budgetsettings`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `level` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `locked_percentage` decimal(5, 2) NOT NULL,
  `warning_threshold` decimal(5, 2) NOT NULL,
  `warning_action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `budget_period_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `budgets_budgetsettin_budget_period_id_4d876a4b_fk_budgets_b`(`budget_period_id` ASC) USING BTREE,
  INDEX `budgets_budgetsettin_organization_id_4597e0aa_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `budgets_budgetsettin_budget_period_id_4d876a4b_fk_budgets_b` FOREIGN KEY (`budget_period_id`) REFERENCES `budgets_budgetperiod` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgetsettin_organization_id_4597e0aa_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgettransaction
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgettransaction`;
CREATE TABLE `budgets_budgettransaction`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `transaction_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25, 2) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_id` bigint NULL DEFAULT NULL,
  `related_tankhah_id` bigint NULL DEFAULT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `transaction_id` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `client_host` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `client_ip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `related_factor_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `transaction_id`(`transaction_id` ASC) USING BTREE,
  INDEX `budgets_budgettransa_allocation_id_3ea01a6b_fk_budgets_b`(`allocation_id` ASC) USING BTREE,
  INDEX `budgets_budgettransa_related_tankhah_id_9dbc06de_fk_tankhah_t`(`related_tankhah_id` ASC) USING BTREE,
  INDEX `budgets_budgettransa_created_by_id_30bcb59a_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `budgets_budgettransa_related_factor_id_193681d2_fk_tankhah_f`(`related_factor_id` ASC) USING BTREE,
  CONSTRAINT `budgets_budgettransa_allocation_id_3ea01a6b_fk_budgets_b` FOREIGN KEY (`allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_created_by_id_30bcb59a_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_related_factor_id_193681d2_fk_tankhah_f` FOREIGN KEY (`related_factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_budgettransa_related_tankhah_id_9dbc06de_fk_tankhah_t` FOREIGN KEY (`related_tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 178 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_budgettransferreturn
-- ----------------------------
DROP TABLE IF EXISTS `budgets_budgettransferreturn`;
CREATE TABLE `budgets_budgettransferreturn`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_costcenter
-- ----------------------------
DROP TABLE IF EXISTS `budgets_costcenter`;
CREATE TABLE `budgets_costcenter`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocated_budget` decimal(25, 2) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `budget_allocation_id` bigint NOT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE,
  INDEX `budgets_costcenter_budget_allocation_id_1f2c1ba7_fk_budgets_b`(`budget_allocation_id` ASC) USING BTREE,
  INDEX `budgets_costcenter_organization_id_3ffab0d4_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `budgets_costcenter_budget_allocation_id_1f2c1ba7_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_costcenter_organization_id_3ffab0d4_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_payee
-- ----------------------------
DROP TABLE IF EXISTS `budgets_payee`;
CREATE TABLE `budgets_payee`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `payee_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `national_id` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `account_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `iban` varchar(34) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `address` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `family` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `legal_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `brand_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `tax_id` varbinary(20) NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `budgets_payee_created_by_id_7753d727_fk_accounts_customuser_id`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `budgets_payee_created_by_id_7753d727_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_paymentorder
-- ----------------------------
DROP TABLE IF EXISTS `budgets_paymentorder`;
CREATE TABLE `budgets_paymentorder`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `order_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `issue_date` date NOT NULL,
  `amount` decimal(25, 2) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `payment_id` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `status_id` int NOT NULL,
  `min_signatures` int NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `created_by_post_id` bigint NULL DEFAULT NULL,
  `payee_id` bigint NULL DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  `payment_date` date NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `is_active` tinyint NULL DEFAULT NULL,
  `related_tankhah_id` tinyint NULL DEFAULT NULL,
  `payee_account_number` bigint NULL DEFAULT NULL,
  `payee_iban` bigint NULL DEFAULT NULL,
  `payment_tracking_id` tinyint NULL DEFAULT NULL,
  `paid_by_id` tinyint NULL DEFAULT NULL,
  `organization_id` tinyint NULL DEFAULT NULL,
  `project_id` tinyint NULL DEFAULT NULL,
  `current_stage_id` tinyint NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  `is_locked` float NULL DEFAULT NULL,
  `notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_archived` float NULL DEFAULT NULL,
  `archived_at` tinyint NULL DEFAULT NULL,
  `archived_by_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `order_number`(`order_number` ASC) USING BTREE,
  INDEX `budgets_paymentorder_created_by_id_1c9df5c8_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `budgets_paymentorder_created_by_post_id_8e17276f_fk_core_post_id`(`created_by_post_id` ASC) USING BTREE,
  INDEX `budgets_paymentorder_payee_id_6ac4b2b3_fk_budgets_payee_id`(`payee_id` ASC) USING BTREE,
  INDEX `budgets_paymentorder_tankhah_id_0a90ef8c_fk_tankhah_tankhah_id`(`tankhah_id` ASC) USING BTREE,
  INDEX `budgets_pay_status__7a985f_idx`(`status_id` ASC, `organization_id` ASC) USING BTREE,
  INDEX `budgets_pay_is_arch_415832_idx`(`is_archived` ASC, `is_locked` ASC) USING BTREE,
  CONSTRAINT `budgets_paymentorder_created_by_id_1c9df5c8_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_created_by_post_id_8e17276f_fk_core_post_id` FOREIGN KEY (`created_by_post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_payee_id_6ac4b2b3_fk_budgets_payee_id` FOREIGN KEY (`payee_id`) REFERENCES `budgets_payee` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_tankhah_id_0a90ef8c_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_paymentorder_related_factors
-- ----------------------------
DROP TABLE IF EXISTS `budgets_paymentorder_related_factors`;
CREATE TABLE `budgets_paymentorder_related_factors`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `paymentorder_id` bigint NOT NULL,
  `factor_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `budgets_paymentorder_rel_paymentorder_id_factor_i_f798b702_uniq`(`paymentorder_id` ASC, `factor_id` ASC) USING BTREE,
  INDEX `budgets_paymentorder_factor_id_66eb4c75_fk_tankhah_f`(`factor_id` ASC) USING BTREE,
  CONSTRAINT `budgets_paymentorder_factor_id_66eb4c75_fk_tankhah_f` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_paymentorder_paymentorder_id_85be9196_fk_budgets_p` FOREIGN KEY (`paymentorder_id`) REFERENCES `budgets_paymentorder` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 6 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_projectbudgetallocation
-- ----------------------------
DROP TABLE IF EXISTS `budgets_projectbudgetallocation`;
CREATE TABLE `budgets_projectbudgetallocation`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `allocated_amount` decimal(25, 2) NOT NULL,
  `allocation_date` date NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `budget_allocation_id` bigint NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `project_id` bigint NOT NULL,
  `subproject_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `returned_amount` decimal(25, 2) NULL DEFAULT NULL,
  `is_locked` tinyint(1) NULL DEFAULT NULL,
  `locked_percentage` decimal(10, 2) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `budgets_projectbudge_budget_allocation_id_4605121d_fk_budgets_b`(`budget_allocation_id` ASC) USING BTREE,
  INDEX `budgets_projectbudge_created_by_id_a7e2ba3a_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `budgets_pro_project_86d725_idx`(`project_id` ASC) USING BTREE,
  INDEX `budgets_pro_subproj_9a9505_idx`(`subproject_id` ASC) USING BTREE,
  CONSTRAINT `budgets_projectbudge_budget_allocation_id_4605121d_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_created_by_id_a7e2ba3a_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_project_id_7606ae30_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `budgets_projectbudge_subproject_id_6210df4a_fk_core_subp` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 50 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for budgets_transactiontype
-- ----------------------------
DROP TABLE IF EXISTS `budgets_transactiontype`;
CREATE TABLE `budgets_transactiontype`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `requires_extra_approval` tinyint(1) NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `transaction_flow` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `name`(`name` ASC) USING BTREE,
  INDEX `budgets_transactiont_created_by_id_bf8f9755_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `budgets_transactiont_created_by_id_bf8f9755_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_accessrule
-- ----------------------------
DROP TABLE IF EXISTS `core_accessrule`;
CREATE TABLE `core_accessrule`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `organization_id` bigint NULL DEFAULT NULL,
  `branch_id` int NULL DEFAULT NULL,
  `stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `action_type` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_payment_order_signer` float NULL DEFAULT NULL,
  `is_active` float NULL DEFAULT NULL,
  `entity_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `post_id` bigint NULL DEFAULT NULL,
  `min_signatures` int UNSIGNED NOT NULL,
  `auto_advance` tinyint(1) NOT NULL,
  `is_final_stage` tinyint(1) NOT NULL,
  `stage_order` int UNSIGNED NULL DEFAULT NULL,
  `triggers_payment_order` tinyint(1) NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `min_level` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_accessrule_post_id_9e70516e_fk_core_post_id`(`post_id` ASC) USING BTREE,
  INDEX `core_accessrule_created_by_id_76af7d97_fk_accounts_customuser_id`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `core_accessrule_created_by_id_76af7d97_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_accessrule_post_id_9e70516e_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_accessrule_chk_1` CHECK (`min_signatures` >= 0),
  CONSTRAINT `core_accessrule_chk_2` CHECK (`stage_order` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 6049 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_action
-- ----------------------------
DROP TABLE IF EXISTS `core_action`;
CREATE TABLE `core_action`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NULL DEFAULT 1,
  `created_by_id` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime(6) NOT NULL,
  `button_style` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `confirmation_message` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `display_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `icon` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 37 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_branch
-- ----------------------------
DROP TABLE IF EXISTS `core_branch`;
CREATE TABLE `core_branch`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(250) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_dashboard_core
-- ----------------------------
DROP TABLE IF EXISTS `core_dashboard_core`;
CREATE TABLE `core_dashboard_core`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_dashboardview
-- ----------------------------
DROP TABLE IF EXISTS `core_dashboardview`;
CREATE TABLE `core_dashboardview`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_dashboardview_flows
-- ----------------------------
DROP TABLE IF EXISTS `core_dashboardview_flows`;
CREATE TABLE `core_dashboardview_flows`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_dashboardwidgetpermissions
-- ----------------------------
DROP TABLE IF EXISTS `core_dashboardwidgetpermissions`;
CREATE TABLE `core_dashboardwidgetpermissions`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_dynamicconfiguration
-- ----------------------------
DROP TABLE IF EXISTS `core_dynamicconfiguration`;
CREATE TABLE `core_dynamicconfiguration`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `key`(`key` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 52 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_entitytype
-- ----------------------------
DROP TABLE IF EXISTS `core_entitytype`;
CREATE TABLE `core_entitytype`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NULL DEFAULT NULL,
  `created_at` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE,
  UNIQUE INDEX `content_type_id`(`content_type_id` ASC) USING BTREE,
  INDEX `core_entitytype_content_type_id_fk_django_co`(`content_type_id` ASC) USING BTREE,
  INDEX `core_entity_code_18637a_idx`(`code` ASC) USING BTREE,
  CONSTRAINT `core_entitytype_content_type_id_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_fontsettings
-- ----------------------------
DROP TABLE IF EXISTS `core_fontsettings`;
CREATE TABLE `core_fontsettings`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `family_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_file` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_format` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `font_weight` int NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `is_rtl_support` tinyint(1) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `file_size` int UNSIGNED NULL DEFAULT NULL,
  `upload_date` datetime(6) NOT NULL,
  `uploaded_by_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_fontsettings_uploaded_by_id_7b218a45_fk_accounts_`(`uploaded_by_id` ASC) USING BTREE,
  CONSTRAINT `core_fontsettings_uploaded_by_id_7b218a45_fk_accounts_` FOREIGN KEY (`uploaded_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_fontsettings_chk_1` CHECK (`file_size` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for core_organization
-- ----------------------------
DROP TABLE IF EXISTS `core_organization`;
CREATE TABLE `core_organization`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `org_type_id` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `parent_organization_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_core` tinyint(1) NOT NULL,
  `is_independent` float NULL DEFAULT NULL,
  `is_holding` float NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE,
  INDEX `core_organi_code_eadc65_idx`(`code` ASC, `org_type_id` ASC) USING BTREE,
  INDEX `core_organization_parent_organization__0e5b8fdd_fk_core_orga`(`parent_organization_id` ASC) USING BTREE,
  CONSTRAINT `core_organization_parent_organization__0e5b8fdd_fk_core_orga` FOREIGN KEY (`parent_organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 10 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_organizationchartapiview
-- ----------------------------
DROP TABLE IF EXISTS `core_organizationchartapiview`;
CREATE TABLE `core_organizationchartapiview`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_organizationchartview
-- ----------------------------
DROP TABLE IF EXISTS `core_organizationchartview`;
CREATE TABLE `core_organizationchartview`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_organizationtype
-- ----------------------------
DROP TABLE IF EXISTS `core_organizationtype`;
CREATE TABLE `core_organizationtype`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `org_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `fname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_budget_allocatable` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `en_name`(`org_type` ASC) USING BTREE,
  UNIQUE INDEX `fname`(`fname` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_permission_allowed_actions
-- ----------------------------
DROP TABLE IF EXISTS `core_permission_allowed_actions`;
CREATE TABLE `core_permission_allowed_actions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `permission_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_post
-- ----------------------------
DROP TABLE IF EXISTS `core_post`;
CREATE TABLE `core_post`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `level` int NOT NULL,
  `branch_id` varchar(3) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `organization_id` bigint NOT NULL,
  `parent_id` bigint NULL DEFAULT NULL,
  `max_change_level` int NOT NULL,
  `is_payment_order_signer` tinyint(1) NOT NULL,
  `can_final_approve_budget` tinyint(1) NOT NULL,
  `can_final_approve_factor` tinyint(1) NOT NULL,
  `can_final_approve_tankhah` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_post_organization_id_7cb921cb_fk_core_organization_id`(`organization_id` ASC) USING BTREE,
  INDEX `core_post_parent_id_f52ad6c0_fk_core_post_id`(`parent_id` ASC) USING BTREE,
  CONSTRAINT `core_post_organization_id_7cb921cb_fk_core_organization_id` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_post_parent_id_f52ad6c0_fk_core_post_id` FOREIGN KEY (`parent_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 46 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_postaction
-- ----------------------------
DROP TABLE IF EXISTS `core_postaction`;
CREATE TABLE `core_postaction`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `post_id` bigint NOT NULL,
  `stage_id` bigint NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `triggers_payment_order` tinyint(1) NOT NULL,
  `min_level` int NULL DEFAULT NULL,
  `allowed_actions` json NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_postaction_stage_id_e86eeb7d_fk_core_workflowstage_id`(`stage_id` ASC) USING BTREE,
  INDEX `core_postaction_post_id_27e16c7b`(`post_id` ASC) USING BTREE,
  CONSTRAINT `core_postaction_post_id_27e16c7b_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 37 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_posthistory
-- ----------------------------
DROP TABLE IF EXISTS `core_posthistory`;
CREATE TABLE `core_posthistory`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `changed_field` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `old_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `new_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `changed_at` datetime(6) NOT NULL,
  `changed_by_id` bigint NULL DEFAULT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_posthistory_changed_by_id_56e23fbe_fk_accounts_`(`changed_by_id` ASC) USING BTREE,
  INDEX `core_posthi_post_id_2c35ae_idx`(`post_id` ASC, `changed_at` ASC) USING BTREE,
  CONSTRAINT `core_posthistory_changed_by_id_56e23fbe_fk_accounts_` FOREIGN KEY (`changed_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_posthistory_post_id_06bedfe1_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 286 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_postruleassignment
-- ----------------------------
DROP TABLE IF EXISTS `core_postruleassignment`;
CREATE TABLE `core_postruleassignment`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `custom_settings` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `post_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  `organization_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_postruleassignm_created_by_id_5a5a4ae7_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `core_postruleassignment_post_id_4638abbc`(`post_id` ASC) USING BTREE,
  INDEX `core_postruleassignment_action_id_9e94943b_fk_core_action_id`(`action_id` ASC) USING BTREE,
  INDEX `core_postruleassignm_organization_id_bd603b1a_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `core_postruleassignm_created_by_id_5a5a4ae7_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignm_organization_id_bd603b1a_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignment_action_id_9e94943b_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_postruleassignment_post_id_4638abbc_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1343 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_project
-- ----------------------------
DROP TABLE IF EXISTS `core_project`;
CREATE TABLE `core_project`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NULL DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `allocations_id` bigint NULL DEFAULT NULL,
  `priority` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 16 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_project_organizations
-- ----------------------------
DROP TABLE IF EXISTS `core_project_organizations`;
CREATE TABLE `core_project_organizations`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `project_id` bigint NOT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `core_project_organizatio_project_id_organization__629c5e5f_uniq`(`project_id` ASC, `organization_id` ASC) USING BTREE,
  INDEX `core_project_organiz_organization_id_2397ad59_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `core_project_organiz_organization_id_2397ad59_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_project_organiz_project_id_235f1848_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 26 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_status
-- ----------------------------
DROP TABLE IF EXISTS `core_status`;
CREATE TABLE `core_status`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_initial` tinyint(1) NOT NULL,
  `is_final_approve` tinyint(1) NOT NULL,
  `is_final_reject` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NULL DEFAULT 1,
  `created_by_id` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime(6) NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_paid` tinyint(1) NOT NULL,
  `is_pending` tinyint(1) NOT NULL,
  `is_rejected` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE,
  INDEX `core_status_code_d5fe62_idx`(`code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 71 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_subproject
-- ----------------------------
DROP TABLE IF EXISTS `core_subproject`;
CREATE TABLE `core_subproject`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `is_active` tinyint(1) NOT NULL,
  `project_id` bigint NOT NULL,
  `allocated_budget` decimal(25, 2) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_subproject_project_id_07e5e283_fk_core_project_id`(`project_id` ASC) USING BTREE,
  CONSTRAINT `core_subproject_project_id_07e5e283_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 7 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_systemsettings
-- ----------------------------
DROP TABLE IF EXISTS `core_systemsettings`;
CREATE TABLE `core_systemsettings`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `budget_locked_percentage_default` decimal(5, 2) NOT NULL,
  `budget_warning_threshold_default` decimal(5, 2) NOT NULL,
  `budget_warning_action_default` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `allocation_locked_percentage_default` decimal(5, 2) NOT NULL,
  `tankhah_used_statuses` json NOT NULL,
  `tankhah_accessible_organizations` json NOT NULL,
  `tankhah_payment_ceiling_default` decimal(25, 0) NULL DEFAULT NULL,
  `tankhah_payment_ceiling_enabled_default` tinyint(1) NULL DEFAULT NULL,
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
  `factor_payment_ceiling_default` decimal(25, 2) NULL DEFAULT NULL,
  `factor_payment_ceiling_enabled_default` tinyint(1) NOT NULL,
  `enforce_tankhah_ceiling_on_factor` tinyint(1) NOT NULL,
  `exclude_expired_tankhah_from_factor_form` tinyint(1) NOT NULL,
  `create_budget_commitment_on_factor_draft` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 3 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_transition
-- ----------------------------
DROP TABLE IF EXISTS `core_transition`;
CREATE TABLE `core_transition`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type_id` bigint NOT NULL,
  `action_id` bigint NOT NULL,
  `from_status_id` bigint NOT NULL,
  `to_status_id` bigint NOT NULL,
  `created_by_id` int NULL DEFAULT NULL,
  `created_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NULL DEFAULT 1,
  `organization_id` int NULL DEFAULT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_transition_action_id_b287ea45_fk_core_action_id`(`action_id` ASC) USING BTREE,
  INDEX `core_transition_from_status_id_7c70969a_fk_core_status_id`(`from_status_id` ASC) USING BTREE,
  INDEX `core_transition_to_status_id_5eaef663_fk_core_status_id`(`to_status_id` ASC) USING BTREE,
  INDEX `core_transition_entity_type_id_1043c22c`(`entity_type_id` ASC) USING BTREE,
  INDEX `core_transi_entity__5109ac_idx`(`entity_type_id` ASC, `organization_id` ASC, `from_status_id` ASC, `is_active` ASC) USING BTREE,
  INDEX `core_transition_organization_id_c6a6b401`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `core_transition_action_id_b287ea45_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_from_status_id_7c70969a_fk_core_status_id` FOREIGN KEY (`from_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_to_status_id_5eaef663_fk_core_status_id` FOREIGN KEY (`to_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 729 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_transition_allowed_posts
-- ----------------------------
DROP TABLE IF EXISTS `core_transition_allowed_posts`;
CREATE TABLE `core_transition_allowed_posts`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `transition_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `core_transition_allowed__transition_id_post_id_bf5dd99e_uniq`(`transition_id` ASC, `post_id` ASC) USING BTREE,
  INDEX `core_transition_allowed_posts_post_id_3c2cc5d5_fk_core_post_id`(`post_id` ASC) USING BTREE,
  CONSTRAINT `core_transition_allo_transition_id_70ee581d_fk_core_tran` FOREIGN KEY (`transition_id`) REFERENCES `core_transition` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transition_allowed_posts_post_id_3c2cc5d5_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1516 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_transitiontemplate
-- ----------------------------
DROP TABLE IF EXISTS `core_transitiontemplate`;
CREATE TABLE `core_transitiontemplate`  (
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
  UNIQUE INDEX `core_transitiontemplate_entity_type_id_action_id_06fa0bbb_uniq`(`entity_type_id` ASC, `action_id` ASC) USING BTREE,
  INDEX `core_transitiontemplate_action_id_03ee8f6d_fk_core_action_id`(`action_id` ASC) USING BTREE,
  INDEX `core_transitiontempl_created_by_id_cd56ddf6_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `core_transitiontempl_created_by_id_cd56ddf6_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_transitiontemplate_action_id_03ee8f6d_fk_core_action_id` FOREIGN KEY (`action_id`) REFERENCES `core_action` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_userpost
-- ----------------------------
DROP TABLE IF EXISTS `core_userpost`;
CREATE TABLE `core_userpost`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `start_date` date NOT NULL,
  `end_date` date NULL DEFAULT NULL,
  `post_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_userpost_post_id_3da85c9b_fk_core_post_id`(`post_id` ASC) USING BTREE,
  INDEX `core_userpost_user_id_d7e77eae`(`user_id` ASC) USING BTREE,
  CONSTRAINT `core_userpost_post_id_3da85c9b_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_userpost_user_id_d7e77eae_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 45 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_workflowruletemplate
-- ----------------------------
DROP TABLE IF EXISTS `core_workflowruletemplate`;
CREATE TABLE `core_workflowruletemplate`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `rules_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_public` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_workflowruletem_created_by_id_182ee905_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `core_workflowruletem_organization_id_b77b7a7e_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `core_workflowruletem_created_by_id_182ee905_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `core_workflowruletem_organization_id_b77b7a7e_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for core_workflowstage
-- ----------------------------
DROP TABLE IF EXISTS `core_workflowstage`;
CREATE TABLE `core_workflowstage`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `order` int UNSIGNED NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_final_stage` tinyint(1) NOT NULL,
  `triggers_payment_order` float NULL DEFAULT NULL,
  `auto_advance` float NULL DEFAULT NULL,
  `entity_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `min_signatures` int UNSIGNED NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `core_workflowstage_entity_type_238ea13d`(`entity_type` ASC) USING BTREE,
  INDEX `core_workfl_entity__89d262_idx`(`entity_type` ASC, `is_active` ASC) USING BTREE,
  CONSTRAINT `core_workflowstage_chk_1` CHECK (`min_signatures` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 13 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for django_admin_log
-- ----------------------------
DROP TABLE IF EXISTS `django_admin_log`;
CREATE TABLE `django_admin_log`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `object_repr` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action_flag` smallint UNSIGNED NOT NULL,
  `change_message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `content_type_id` int NULL DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `django_admin_log_user_id_c564eba6_fk_accounts_customuser_id`(`user_id` ASC) USING BTREE,
  INDEX `django_admin_log_content_type_id_c4bce8eb_fk`(`content_type_id` ASC) USING BTREE,
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `django_admin_log_chk_1` CHECK (`action_flag` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 55 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for django_content_type
-- ----------------------------
DROP TABLE IF EXISTS `django_content_type`;
CREATE TABLE `django_content_type`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `django_content_type_app_label_model_76bd3d3b_uniq`(`app_label` ASC, `model` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 159 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for django_migrations
-- ----------------------------
DROP TABLE IF EXISTS `django_migrations`;
CREATE TABLE `django_migrations`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `app` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 366 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for django_session
-- ----------------------------
DROP TABLE IF EXISTS `django_session`;
CREATE TABLE `django_session`  (
  `session_key` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `session_data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`) USING BTREE,
  INDEX `django_session_expire_date_a5c62663`(`expire_date` ASC) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_backuplog
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_backuplog`;
CREATE TABLE `notificationapp_backuplog`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `started_at` datetime(6) NOT NULL,
  `finished_at` datetime(6) NULL DEFAULT NULL,
  `duration` bigint NULL DEFAULT NULL,
  `file_size` bigint NULL DEFAULT NULL,
  `file_path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `error_message` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `details` json NOT NULL,
  `schedule_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `notificationApp_back_schedule_id_90087260_fk_notificat`(`schedule_id` ASC) USING BTREE,
  CONSTRAINT `notificationApp_back_schedule_id_90087260_fk_notificat` FOREIGN KEY (`schedule_id`) REFERENCES `notificationapp_backupschedule` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 5 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_backupschedule
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_backupschedule`;
CREATE TABLE `notificationapp_backupschedule`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `frequency` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `custom_cron` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `database` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `format_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `encrypt` tinyint(1) NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `last_run` datetime(6) NULL DEFAULT NULL,
  `next_run` datetime(6) NULL DEFAULT NULL,
  `notify_on_success` tinyint(1) NOT NULL,
  `notify_on_failure` tinyint(1) NOT NULL,
  `created_by_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `notificationApp_back_created_by_id_5e101a27_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `notificationApp_back_created_by_id_5e101a27_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_backupschedule_notify_recipients
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_backupschedule_notify_recipients`;
CREATE TABLE `notificationapp_backupschedule_notify_recipients`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `backupschedule_id` bigint NOT NULL,
  `customuser_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `notificationApp_backupsc_backupschedule_id_custom_48ac7dda_uniq`(`backupschedule_id` ASC, `customuser_id` ASC) USING BTREE,
  INDEX `notificationApp_back_customuser_id_0dea04f9_fk_accounts_`(`customuser_id` ASC) USING BTREE,
  CONSTRAINT `notificationApp_back_backupschedule_id_4390550e_fk_notificat` FOREIGN KEY (`backupschedule_id`) REFERENCES `notificationapp_backupschedule` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notificationApp_back_customuser_id_0dea04f9_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_notification
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_notification`;
CREATE TABLE `notificationapp_notification`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `verb` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `unread` tinyint(1) NOT NULL,
  `deleted` tinyint(1) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `priority` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `target_object_id` int UNSIGNED NULL DEFAULT NULL,
  `actor_id` bigint NULL DEFAULT NULL,
  `recipient_id` bigint NOT NULL,
  `target_content_type_id` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `notificationApp_noti_actor_id_b13c13c5_fk_accounts_`(`actor_id` ASC) USING BTREE,
  INDEX `notificationApp_noti_recipient_id_5f46c8a3_fk_accounts_`(`recipient_id` ASC) USING BTREE,
  INDEX `notificationApp_noti_target_content_type__c3ec6fd6_fk_django_co`(`target_content_type_id` ASC) USING BTREE,
  CONSTRAINT `notificationApp_noti_actor_id_b13c13c5_fk_accounts_` FOREIGN KEY (`actor_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notificationApp_noti_recipient_id_5f46c8a3_fk_accounts_` FOREIGN KEY (`recipient_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notificationApp_noti_target_content_type__c3ec6fd6_fk_django_co` FOREIGN KEY (`target_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notificationapp_notification_chk_1` CHECK (`target_object_id` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 186 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_notificationrule
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_notificationrule`;
CREATE TABLE `notificationapp_notificationrule`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `priority` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `channel` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 28 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notificationapp_notificationrule_recipients
-- ----------------------------
DROP TABLE IF EXISTS `notificationapp_notificationrule_recipients`;
CREATE TABLE `notificationapp_notificationrule_recipients`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `notificationrule_id` bigint NOT NULL,
  `post_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `notificationApp_notifica_notificationrule_id_post_ee1e8aa8_uniq`(`notificationrule_id` ASC, `post_id` ASC) USING BTREE,
  INDEX `notificationApp_noti_post_id_6348887d_fk_core_post`(`post_id` ASC) USING BTREE,
  CONSTRAINT `notificationApp_noti_notificationrule_id_fe2eb4af_fk_notificat` FOREIGN KEY (`notificationrule_id`) REFERENCES `notificationapp_notificationrule` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notificationApp_noti_post_id_6348887d_fk_core_post` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for notifications_notification
-- ----------------------------
DROP TABLE IF EXISTS `notifications_notification`;
CREATE TABLE `notifications_notification`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `level` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `unread` tinyint(1) NOT NULL,
  `actor_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `verb` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `target_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `action_object_object_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  `public` tinyint(1) NOT NULL,
  `deleted` tinyint(1) NOT NULL,
  `emailed` tinyint(1) NOT NULL,
  `data` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `action_object_content_type_id` int NULL DEFAULT NULL,
  `actor_content_type_id` int NOT NULL,
  `recipient_id` bigint NOT NULL,
  `target_content_type_id` int NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `notifications_notifi_action_object_conten_7d2b8ee9_fk_django_co`(`action_object_content_type_id` ASC) USING BTREE,
  INDEX `notifications_notifi_actor_content_type_i_0c69d7b7_fk_django_co`(`actor_content_type_id` ASC) USING BTREE,
  INDEX `notifications_notifi_recipient_id_d055f3f0_fk_accounts_`(`recipient_id` ASC) USING BTREE,
  INDEX `notifications_notifi_target_content_type__ccb24d88_fk_django_co`(`target_content_type_id` ASC) USING BTREE,
  INDEX `notifications_notification_unread_cce4be30`(`unread` ASC) USING BTREE,
  INDEX `notifications_notification_timestamp_6a797bad`(`timestamp` ASC) USING BTREE,
  INDEX `notifications_notification_public_1bc30b1c`(`public` ASC) USING BTREE,
  INDEX `notifications_notification_deleted_b32b69e6`(`deleted` ASC) USING BTREE,
  INDEX `notifications_notification_emailed_23a5ad81`(`emailed` ASC) USING BTREE,
  CONSTRAINT `notifications_notifi_action_object_conten_7d2b8ee9_fk_django_co` FOREIGN KEY (`action_object_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_actor_content_type_i_0c69d7b7_fk_django_co` FOREIGN KEY (`actor_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_recipient_id_d055f3f0_fk_accounts_` FOREIGN KEY (`recipient_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `notifications_notifi_target_content_type__ccb24d88_fk_django_co` FOREIGN KEY (`target_content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 73 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for purchase_requests_purchaserequest
-- ----------------------------
DROP TABLE IF EXISTS `purchase_requests_purchaserequest`;
CREATE TABLE `purchase_requests_purchaserequest`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `date` date NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `project_id` bigint NULL DEFAULT NULL,
  `status_id` bigint NULL DEFAULT NULL,
  `subproject_id` bigint NULL DEFAULT NULL,
  `external_id` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `external_payload` json NULL,
  `is_synced` tinyint(1) NOT NULL,
  `source_system` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `synced_at` datetime(6) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `number`(`number` ASC) USING BTREE,
  INDEX `purchase_requests_pu_created_by_id_34412446_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  INDEX `purchase_requests_pu_project_id_240fc284_fk_core_proj`(`project_id` ASC) USING BTREE,
  INDEX `purchase_requests_pu_status_id_d5be6761_fk_core_stat`(`status_id` ASC) USING BTREE,
  INDEX `purchase_requests_pu_subproject_id_5f0583cc_fk_core_subp`(`subproject_id` ASC) USING BTREE,
  INDEX `purchase_re_number_6001f3_idx`(`number` ASC) USING BTREE,
  INDEX `purchase_re_organiz_fbb6d0_idx`(`organization_id` ASC, `date` ASC) USING BTREE,
  INDEX `purchase_re_source__d17c02_idx`(`source_system` ASC, `external_id` ASC) USING BTREE,
  CONSTRAINT `purchase_requests_pu_created_by_id_34412446_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_organization_id_f2200998_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_project_id_240fc284_fk_core_proj` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_status_id_d5be6761_fk_core_stat` FOREIGN KEY (`status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `purchase_requests_pu_subproject_id_5f0583cc_fk_core_subp` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for purchase_requests_purchaserequestitem
-- ----------------------------
DROP TABLE IF EXISTS `purchase_requests_purchaserequestitem`;
CREATE TABLE `purchase_requests_purchaserequestitem`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `quantity` decimal(25, 2) NOT NULL,
  `unit_price` decimal(25, 2) NOT NULL,
  `amount` decimal(25, 2) NOT NULL,
  `request_id` bigint NOT NULL,
  `external_item_id` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `sku` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `uom` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `purchase_re_request_c03fee_idx`(`request_id` ASC) USING BTREE,
  INDEX `purchase_re_sku_414960_idx`(`sku` ASC) USING BTREE,
  CONSTRAINT `purchase_requests_pu_request_id_d410aad4_fk_purchase_` FOREIGN KEY (`request_id`) REFERENCES `purchase_requests_purchaserequest` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for reports_reportsapis
-- ----------------------------
DROP TABLE IF EXISTS `reports_reportsapis`;
CREATE TABLE `reports_reportsapis`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for reports_reportsdashboard
-- ----------------------------
DROP TABLE IF EXISTS `reports_reportsdashboard`;
CREATE TABLE `reports_reportsdashboard`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for reports_send_to_accounting
-- ----------------------------
DROP TABLE IF EXISTS `reports_send_to_accounting`;
CREATE TABLE `reports_send_to_accounting`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for reports_tankhah_financialreport
-- ----------------------------
DROP TABLE IF EXISTS `reports_tankhah_financialreport`;
CREATE TABLE `reports_tankhah_financialreport`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for reports_tankhahdetailview
-- ----------------------------
DROP TABLE IF EXISTS `reports_tankhahdetailview`;
CREATE TABLE `reports_tankhahdetailview`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_approvallog
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_approvallog`;
CREATE TABLE `tankhah_approvallog`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `comment` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `timestamp` datetime(6) NOT NULL,
  `changed_field` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `seen_by_higher` tinyint(1) NOT NULL,
  `seen_at` datetime(6) NULL DEFAULT NULL,
  `post_id` bigint NULL DEFAULT NULL,
  `stage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  `factor_id` bigint NULL DEFAULT NULL,
  `factor_item_id` bigint NULL DEFAULT NULL,
  `tankhah_id` bigint NULL DEFAULT NULL,
  `content_type_id` int NULL DEFAULT NULL,
  `object_id` int UNSIGNED NOT NULL,
  `is_final_approval` tinyint(1) NOT NULL,
  `stage_order` int UNSIGNED NULL DEFAULT NULL,
  `stage_id` int NULL DEFAULT NULL,
  `is_temporary` tinyint NULL DEFAULT NULL,
  `stage_rule_id` bigint NULL DEFAULT NULL,
  `from_status_id` bigint NOT NULL,
  `to_status_id` bigint NULL DEFAULT NULL,
  `action_id` bigint NULL DEFAULT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_admin_action` tinyint(1) NULL DEFAULT 0,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_approvallog_post_id_25bdf3fb_fk_core_post_id`(`post_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_user_id_90f106ab_fk_accounts_customuser_id`(`user_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_factor_id_37f79ad1_fk_tankhah_factor_id`(`factor_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_factor_item_id_34ec4a58_fk_tankhah_f`(`factor_item_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_tankhah_id_e5d39b2f_fk_tankhah_tankhah_id`(`tankhah_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_content_type_id_2fb149e4_fk_django_co`(`content_type_id` ASC) USING BTREE,
  INDEX `tankhah_app_factor__add5d7_idx`(`factor_id` ASC, `tankhah_id` ASC, `user_id` ASC, `stage` ASC) USING BTREE,
  INDEX `tankhah_approvallog_from_status_id_3559100a_fk_core_status_id`(`from_status_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_stage_rule_id_c3925304_fk_core_status_id`(`stage_rule_id` ASC) USING BTREE,
  INDEX `tankhah_approvallog_created_by_id_033c0640_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_approvallog_content_type_id_2fb149e4_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_created_by_id_033c0640_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_factor_id_37f79ad1_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_factor_item_id_34ec4a58_fk_tankhah_f` FOREIGN KEY (`factor_item_id`) REFERENCES `tankhah_factoritem` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_from_status_id_3559100a_fk_core_status_id` FOREIGN KEY (`from_status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_post_id_25bdf3fb_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_stage_rule_id_c3925304_fk_core_status_id` FOREIGN KEY (`stage_rule_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_tankhah_id_e5d39b2f_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_user_id_90f106ab_fk_accounts_customuser_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_approvallog_chk_1` CHECK (`object_id` >= 0),
  CONSTRAINT `tankhah_approvallog_chk_2` CHECK (`stage_order` >= 0)
) ENGINE = InnoDB AUTO_INCREMENT = 342 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_dashboard_tankhah
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_dashboard_tankhah`;
CREATE TABLE `tankhah_dashboard_tankhah`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_factor
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_factor`;
CREATE TABLE `tankhah_factor`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `date` date NOT NULL,
  `amount` decimal(20, 2) NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `status_id` bigint NULL DEFAULT NULL,
  `locked_by_stage_id` bigint NULL DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  `budget` decimal(20, 2) NOT NULL,
  `remaining_budget` decimal(20, 2) NOT NULL,
  `created_by_id` bigint NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_emergency` tinyint(1) NOT NULL,
  `category_id` bigint NOT NULL,
  `is_locked` tinyint(1) NULL DEFAULT 0,
  `re_registered_in_id` bigint NULL DEFAULT NULL,
  `rejected_reason` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `deleted_at` datetime(6) NULL DEFAULT NULL,
  `deleted_by_id` bigint NULL DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `payee_id` bigint NULL DEFAULT NULL,
  `archived_at` datetime(6) NULL DEFAULT NULL,
  `archived_by_id` bigint NULL DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `purchase_request_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_factor_tankhah_id_b1fd1df3_fk_tankhah_tankhah_id`(`tankhah_id` ASC) USING BTREE,
  INDEX `tankhah_factor_locked_by_stage_id_a274da7d_fk_core_work`(`locked_by_stage_id` ASC) USING BTREE,
  INDEX `tankhah_factor_created_by_id_b06575df_fk_accounts_customuser_id`(`created_by_id` ASC) USING BTREE,
  INDEX `tankhah_factor_category_id_4e863d6f_fk_tankhah_itemcategory_id`(`category_id` ASC) USING BTREE,
  INDEX `tankhah_factor_re_registered_in_id_a27b90b0_fk_tankhah_t`(`re_registered_in_id` ASC) USING BTREE,
  INDEX `tankhah_factor_deleted_by_id_877ae561_fk_accounts_customuser_id`(`deleted_by_id` ASC) USING BTREE,
  INDEX `tankhah_factor_status_id_fk_core_status_id`(`status_id` ASC) USING BTREE,
  INDEX `tankhah_factor_archived_by_id_785e6d61_fk_accounts_customuser_id`(`archived_by_id` ASC) USING BTREE,
  INDEX `tankhah_factor_purchase_request_id_d703a494_fk_purchase_`(`purchase_request_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_factor_archived_by_id_785e6d61_fk_accounts_customuser_id` FOREIGN KEY (`archived_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_category_id_4e863d6f_fk_tankhah_itemcategory_id` FOREIGN KEY (`category_id`) REFERENCES `tankhah_itemcategory` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_created_by_id_b06575df_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_deleted_by_id_877ae561_fk_accounts_customuser_id` FOREIGN KEY (`deleted_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_locked_by_stage_id_a274da7d_fk_core_status_id` FOREIGN KEY (`locked_by_stage_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_purchase_request_id_d703a494_fk_purchase_` FOREIGN KEY (`purchase_request_id`) REFERENCES `purchase_requests_purchaserequest` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_re_registered_in_id_a27b90b0_fk_tankhah_t` FOREIGN KEY (`re_registered_in_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_status_id_fk_core_status_id` FOREIGN KEY (`status_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factor_tankhah_id_b1fd1df3_fk_tankhah_tankhah_id` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 89 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_factordocument
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_factordocument`;
CREATE TABLE `tankhah_factordocument`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `file_size` int NULL DEFAULT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `factor_id` bigint NOT NULL,
  `uploaded_by_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_factordocument_factor_id_5f2b8fc0_fk_tankhah_factor_id`(`factor_id` ASC) USING BTREE,
  INDEX `tankhah_factordocume_uploaded_by_id_efc84e28_fk_accounts_`(`uploaded_by_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_factordocume_uploaded_by_id_efc84e28_fk_accounts_` FOREIGN KEY (`uploaded_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factordocument_factor_id_5f2b8fc0_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 10 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_factorhistory
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_factorhistory`;
CREATE TABLE `tankhah_factorhistory`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `change_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `change_timestamp` datetime(6) NOT NULL,
  `old_data` json NULL,
  `new_data` json NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `changed_by_id` bigint NULL DEFAULT NULL,
  `factor_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_factorhistor_changed_by_id_29dcfeeb_fk_accounts_`(`changed_by_id` ASC) USING BTREE,
  INDEX `tankhah_factorhistory_factor_id_5bd16d12_fk_tankhah_factor_id`(`factor_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_factorhistor_changed_by_id_29dcfeeb_fk_accounts_` FOREIGN KEY (`changed_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_factorhistory_factor_id_5bd16d12_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1919 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_factoritem
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_factoritem`;
CREATE TABLE `tankhah_factoritem`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25, 2) NOT NULL,
  `status_id` bigint NULL DEFAULT NULL,
  `quantity` decimal(25, 2) NOT NULL,
  `unit_price` decimal(25, 1) NOT NULL,
  `factor_id` bigint NOT NULL,
  `min_stage_order` int NOT NULL,
  `created_at` datetime NULL DEFAULT NULL,
  `updated_at` datetime NULL DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_factoritem_factor_id_2bb74929_fk_tankhah_factor_id`(`factor_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_factoritem_factor_id_2bb74929_fk_tankhah_factor_id` FOREIGN KEY (`factor_id`) REFERENCES `tankhah_factor` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 111 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_itemcategory
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_itemcategory`;
CREATE TABLE `tankhah_itemcategory`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `min_stage_order` int NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 9 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_stageapprover
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_stageapprover`;
CREATE TABLE `tankhah_stageapprover`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_active` tinyint(1) NOT NULL,
  `post_id` bigint NOT NULL,
  `stage_id` bigint NOT NULL,
  `entity_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `organization_id` bigint NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `tankhah_stageapprover_stage_id_post_id_entity__9b6c6913_uniq`(`stage_id` ASC, `post_id` ASC, `entity_type` ASC, `organization_id` ASC) USING BTREE,
  INDEX `tankhah_stageapprover_post_id_1d6b0b80`(`post_id` ASC) USING BTREE,
  INDEX `tankhah_stageapprover_stage_id_d82b75e0`(`stage_id` ASC) USING BTREE,
  INDEX `tankhah_stageapprove_organization_id_3ea4ea52_fk_core_orga`(`organization_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_stageapprove_organization_id_3ea4ea52_fk_core_orga` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_stageapprover_post_id_1d6b0b80_fk_core_post_id` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 17 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhactiontype
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhactiontype`;
CREATE TABLE `tankhah_tankhactiontype`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action_type` varchar(25) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `code`(`code` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhah
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhah`;
CREATE TABLE `tankhah_tankhah`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `number` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `amount` decimal(25, 2) NOT NULL,
  `date` datetime(6) NOT NULL,
  `due_date` datetime(6) NULL DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `letter_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status_id` bigint NOT NULL,
  `is_archived` tinyint(1) NOT NULL,
  `payment_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  `is_locked` tinyint(1) NOT NULL,
  `archived_at` datetime(6) NULL DEFAULT NULL,
  `canceled` tinyint(1) NOT NULL,
  `created_by_id` bigint NULL DEFAULT NULL,
  `last_stopped_post_id` bigint NULL DEFAULT NULL,
  `organization_id` bigint NOT NULL,
  `project_id` bigint NULL DEFAULT NULL,
  `subproject_id` bigint NULL DEFAULT NULL,
  `remaining_budget` decimal(25, 2) NOT NULL,
  `budget_allocation_id` bigint NULL DEFAULT NULL,
  `is_emergency` tinyint(1) NOT NULL,
  `request_date` date NOT NULL,
  `project_budget_allocation_id` bigint NULL DEFAULT NULL,
  `payment_ceiling` decimal(10, 0) NULL DEFAULT NULL,
  `is_payment_ceiling_enabled` tinyint(1) NULL DEFAULT 0,
  `current_stage_id` bigint NULL DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `number`(`number` ASC) USING BTREE,
  INDEX `tankhah_tan_number_dd4c50_idx`(`number` ASC, `date` ASC, `status_id` ASC, `organization_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_created_by_id_b29865c0_fk_accounts_customuser_id`(`created_by_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_last_stopped_post_id_7592e558_fk_core_post_id`(`last_stopped_post_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_organization_id_01642aa9_fk_core_organization_id`(`organization_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_project_id_54b0b7e7_fk_core_project_id`(`project_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_subproject_id_d314449d_fk_core_subproject_id`(`subproject_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_budget_allocation_id_25455474_fk_budgets_b`(`budget_allocation_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_project_budget_alloc_5eeaa99b_fk_budgets_p`(`project_budget_allocation_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_current_stage_id_e5890193_fk_core_status_id`(`current_stage_id` ASC) USING BTREE,
  INDEX `tankhah_tan_number_ddd2e8_idx`(`number` ASC, `date` ASC, `status_id` ASC, `organization_id` ASC, `project_id` ASC, `created_at` ASC) USING BTREE,
  CONSTRAINT `tankhah_tankhah_budget_allocation_id_25455474_fk_budgets_b` FOREIGN KEY (`budget_allocation_id`) REFERENCES `budgets_budgetallocation` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_created_by_id_b29865c0_fk_accounts_customuser_id` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_current_stage_id_e5890193_fk_core_status_id` FOREIGN KEY (`current_stage_id`) REFERENCES `core_status` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_last_stopped_post_id_7592e558_fk_core_post_id` FOREIGN KEY (`last_stopped_post_id`) REFERENCES `core_post` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_organization_id_01642aa9_fk_core_organization_id` FOREIGN KEY (`organization_id`) REFERENCES `core_organization` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_project_id_54b0b7e7_fk_core_project_id` FOREIGN KEY (`project_id`) REFERENCES `core_project` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_subproject_id_d314449d_fk_core_subproject_id` FOREIGN KEY (`subproject_id`) REFERENCES `core_subproject` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 29 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhah_approved_by
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhah_approved_by`;
CREATE TABLE `tankhah_tankhah_approved_by`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `tankhah_id` bigint NOT NULL,
  `customuser_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `tankhah_tankhah_approved_tankhah_id_customuser_id_46225e0c_uniq`(`tankhah_id` ASC, `customuser_id` ASC) USING BTREE,
  INDEX `tankhah_tankhah_appr_customuser_id_8ddccd3b_fk_accounts_`(`customuser_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_tankhah_appr_customuser_id_8ddccd3b_fk_accounts_` FOREIGN KEY (`customuser_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_tankhah_appr_tankhah_id_1877bab9_fk_tankhah_t` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhahaction
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhahaction`;
CREATE TABLE `tankhah_tankhahaction`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `tankhah_id` bigint NOT NULL,
  `amount` decimal(25, 2) NULL DEFAULT NULL,
  `stage_id` bigint NOT NULL,
  `post_id` bigint NULL DEFAULT NULL,
  `user_id` bigint NULL DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `reference_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '',
  `action_type_id` bigint NULL DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_action_tankhah_fk`(`tankhah_id` ASC) USING BTREE,
  INDEX `tankhah_action_stage_fk`(`stage_id` ASC) USING BTREE,
  INDEX `tankhah_action_post_fk`(`post_id` ASC) USING BTREE,
  INDEX `tankhah_action_user_fk`(`user_id` ASC) USING BTREE,
  INDEX `tankhah_action_actiontype_fk`(`action_type_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_action_actiontype_fk` FOREIGN KEY (`action_type_id`) REFERENCES `budgets_transactiontype` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_post_fk` FOREIGN KEY (`post_id`) REFERENCES `core_post` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_stage_fk` FOREIGN KEY (`stage_id`) REFERENCES `core_workflowstage` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_tankhah_fk` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `tankhah_action_user_fk` FOREIGN KEY (`user_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE SET NULL ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhahdocument
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhahdocument`;
CREATE TABLE `tankhah_tankhahdocument`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `document` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `file_size` int NULL DEFAULT NULL,
  `tankhah_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `tankhah_tankhahdocum_tankhah_id_a34f34d7_fk_tankhah_t`(`tankhah_id` ASC) USING BTREE,
  CONSTRAINT `tankhah_tankhahdocum_tankhah_id_a34f34d7_fk_tankhah_t` FOREIGN KEY (`tankhah_id`) REFERENCES `tankhah_tankhah` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for tankhah_tankhahfinalapproval
-- ----------------------------
DROP TABLE IF EXISTS `tankhah_tankhahfinalapproval`;
CREATE TABLE `tankhah_tankhahfinalapproval`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for version_tracker_appversion
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_appversion`;
CREATE TABLE `version_tracker_appversion`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `version_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `version_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `release_date` datetime(6) NOT NULL,
  `code_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `changed_files` json NOT NULL,
  `system_info` json NOT NULL,
  `author_id` bigint NOT NULL,
  `major` int UNSIGNED NOT NULL DEFAULT 0,
  `minor` int UNSIGNED NOT NULL DEFAULT 0,
  `patch` int UNSIGNED NOT NULL DEFAULT 0,
  `build` int UNSIGNED NOT NULL DEFAULT 0,
  `previous_version_id` bigint NULL DEFAULT NULL,
  `is_final` tinyint(1) NOT NULL DEFAULT 0,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_version`(`app_name` ASC, `major` ASC, `minor` ASC, `patch` ASC, `build` ASC) USING BTREE,
  INDEX `idx_app_name`(`app_name` ASC) USING BTREE,
  INDEX `idx_version_number`(`version_number` ASC) USING BTREE,
  INDEX `idx_release_date`(`release_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2685 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for version_tracker_backuplocation
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_backuplocation`;
CREATE TABLE `version_tracker_backuplocation`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `location_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `is_default` tinyint(1) NOT NULL,
  `is_encrypted` tinyint(1) NOT NULL,
  `max_size_gb` int NULL DEFAULT NULL,
  `description` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `created_at` datetime(6) NOT NULL,
  `last_tested` datetime(6) NULL DEFAULT NULL,
  `last_error` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL,
  `created_by_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `version_tracker_back_created_by_id_c55eccd4_fk_accounts_`(`created_by_id` ASC) USING BTREE,
  CONSTRAINT `version_tracker_back_created_by_id_c55eccd4_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_customuser` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for version_tracker_codechangelog
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_codechangelog`;
CREATE TABLE `version_tracker_codechangelog`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_id` bigint NOT NULL,
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `change_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'modified',
  `change_date` datetime(6) NOT NULL,
  `old_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `new_code` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_version_file`(`version_id` ASC, `file_name` ASC) USING BTREE,
  INDEX `idx_version`(`version_id` ASC) USING BTREE,
  INDEX `idx_change_date`(`change_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 31669 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for version_tracker_filehash
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_filehash`;
CREATE TABLE `version_tracker_filehash`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app_version_id` bigint NOT NULL,
  `file_path` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `hash_value` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_file_version`(`app_version_id` ASC, `file_path` ASC) USING BTREE,
  INDEX `idx_app_version`(`app_version_id` ASC) USING BTREE,
  INDEX `idx_timestamp`(`timestamp` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 108212 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = DYNAMIC;

-- ----------------------------
-- Table structure for version_tracker_finalversion
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_finalversion`;
CREATE TABLE `version_tracker_finalversion`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `release_date` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `idx_release_date`(`release_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for version_tracker_finalversion_app_versions
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_finalversion_app_versions`;
CREATE TABLE `version_tracker_finalversion_app_versions`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `finalversion_id` bigint NOT NULL,
  `appversion_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_final_app`(`finalversion_id` ASC, `appversion_id` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 284 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Procedure structure for AddAllowedPostsByLevel
-- ----------------------------
DROP PROCEDURE IF EXISTS `AddAllowedPostsByLevel`;
delimiter ;;
CREATE PROCEDURE `AddAllowedPostsByLevel`(IN p_transition_id INT,
  IN p_org INT,
  IN p_level INT)
BEGIN
  INSERT INTO core_transition_allowed_posts(transition_id, post_id)
  SELECT p_transition_id, p.id
  FROM core_post p
  WHERE p.organization_id=p_org AND p.is_active=1 AND p.level=p_level
    AND NOT EXISTS (
      SELECT 1 FROM core_transition_allowed_posts ap
      WHERE ap.transition_id=p_transition_id AND ap.post_id=p.id
    );
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for BuildAllFactorWorkflows
-- ----------------------------
DROP PROCEDURE IF EXISTS `BuildAllFactorWorkflows`;
delimiter ;;
CREATE PROCEDURE `BuildAllFactorWorkflows`()
BEGIN
  DECLARE v_org INT;
  DECLARE done INT DEFAULT 0;
  DECLARE cur_org CURSOR FOR
    SELECT DISTINCT organization_id FROM core_post WHERE is_active=1 AND organization_id IS NOT NULL;
  DECLARE CONTINUE HANDLER FOR NOT FOUND SET done=1;

  OPEN cur_org;
  loop_org: LOOP
    FETCH cur_org INTO v_org;
    IF done=1 THEN LEAVE loop_org; END IF;
    CALL BuildFactorWorkflowForOrg(v_org);
  END LOOP;
  CLOSE cur_org;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for BuildFactorWorkflowForOrg
-- ----------------------------
DROP PROCEDURE IF EXISTS `BuildFactorWorkflowForOrg`;
delimiter ;;
CREATE PROCEDURE `BuildFactorWorkflowForOrg`(IN p_org INT)
BEGIN
  DECLARE v_has_l7 INT DEFAULT 0;
  DECLARE v_has_l6 INT DEFAULT 0;
  DECLARE v_has_l1 INT DEFAULT 0;
  DECLARE v_tid INT;

  SELECT EXISTS(SELECT 1 FROM core_post WHERE organization_id=p_org AND is_active=1 AND level=7) INTO v_has_l7;
  SELECT EXISTS(SELECT 1 FROM core_post WHERE organization_id=p_org AND is_active=1 AND level=6) INTO v_has_l6;
  SELECT EXISTS(SELECT 1 FROM core_post WHERE organization_id=p_org AND is_active=1 AND level=1) INTO v_has_l1;

  -- L7
  IF v_has_l7=1 THEN
    CALL EnsureTransition('ارسال (L7): پیش‌نویس → انتظار تأیید', p_org, @ST_DRAFT, @ACT_SUBMIT, @ST_PENDING, @ET_FACTOR, v_tid);
    CALL AddAllowedPostsByLevel(v_tid, p_org, 7);
  END IF;

  -- L6
  IF v_has_l6=1 THEN
    CALL EnsureTransition('تأیید (L6): انتظار تأیید → تأیید میانی', p_org, @ST_PENDING, @ACT_APPROVE, @ST_INTER, @ET_FACTOR, v_tid);
    CALL AddAllowedPostsByLevel(v_tid, p_org, 6);

    CALL EnsureTransition('رد (L6): انتظار تأیید → رد شده', p_org, @ST_PENDING, @ACT_REJECT, @ST_REJ, @ET_FACTOR, v_tid);
    CALL AddAllowedPostsByLevel(v_tid, p_org, 6);
  END IF;

  -- L5..2
  BEGIN
    DECLARE v_lvl INT;
    DECLARE done INT DEFAULT 0;
    DECLARE cur CURSOR FOR
      SELECT DISTINCT level FROM core_post
      WHERE organization_id=p_org AND is_active=1 AND level BETWEEN 2 AND 5
      ORDER BY level DESC;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done=1;

    OPEN cur;
    read_loop: LOOP
      FETCH cur INTO v_lvl;
      IF done=1 THEN LEAVE read_loop; END IF;

      CALL EnsureTransition(CONCAT('تأیید (L', v_lvl, '): تأیید میانی → تأیید میانی'), p_org, @ST_INTER, @ACT_APPROVE, @ST_INTER, @ET_FACTOR, v_tid);
      CALL AddAllowedPostsByLevel(v_tid, p_org, v_lvl);

      CALL EnsureTransition(CONCAT('رد (L', v_lvl, '): تأیید میانی → رد شده'), p_org, @ST_INTER, @ACT_REJECT, @ST_REJ, @ET_FACTOR, v_tid);
      CALL AddAllowedPostsByLevel(v_tid, p_org, v_lvl);
    END LOOP;
    CLOSE cur;
  END;

  -- L1
  IF v_has_l1=1 THEN
    CALL EnsureTransition('تأیید نهایی (L1): تأیید میانی → تأیید نهایی', p_org, @ST_INTER, @ACT_FINAL, @ST_FINAL, @ET_FACTOR, v_tid);
    CALL AddAllowedPostsByLevel(v_tid, p_org, 1);

    CALL EnsureTransition('رد (L1): تأیید میانی → رد شده', p_org, @ST_INTER, @ACT_REJECT, @ST_REJ, @ET_FACTOR, v_tid);
    CALL AddAllowedPostsByLevel(v_tid, p_org, 1);
  END IF;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for EnsureAction
-- ----------------------------
DROP PROCEDURE IF EXISTS `EnsureAction`;
delimiter ;;
CREATE PROCEDURE `EnsureAction`(IN p_code VARCHAR(50),
    IN p_name VARCHAR(255),
    IN p_description VARCHAR(255),
    IN p_is_active TINYINT,
    IN p_created_by_id INT,
    OUT p_id INT)
BEGIN
    DECLARE existing_id INT;
    SELECT id INTO existing_id FROM core_action WHERE code = p_code;
    IF existing_id IS NULL THEN
        INSERT INTO core_action (name, code, description, is_active, created_by_id, created_at)
        VALUES (p_name, p_code, p_description, p_is_active, p_created_by_id, NOW());
        SET p_id = LAST_INSERT_ID();
    ELSE
        SET p_id = existing_id;
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for EnsureEntityType
-- ----------------------------
DROP PROCEDURE IF EXISTS `EnsureEntityType`;
delimiter ;;
CREATE PROCEDURE `EnsureEntityType`(IN p_code VARCHAR(50),
    IN p_name VARCHAR(255),
    OUT p_id INT)
BEGIN
    DECLARE existing_id INT;
    SELECT id INTO existing_id FROM core_entitytype WHERE code = p_code;
    IF existing_id IS NULL THEN
        INSERT INTO core_entitytype (name, code, content_type_id) VALUES (p_name, p_code, NULL);
        SET p_id = LAST_INSERT_ID();
    ELSE
        SET p_id = existing_id;
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for EnsureStatus
-- ----------------------------
DROP PROCEDURE IF EXISTS `EnsureStatus`;
delimiter ;;
CREATE PROCEDURE `EnsureStatus`(IN p_code VARCHAR(50),
    IN p_name VARCHAR(255),
    IN p_description VARCHAR(255),
    IN p_is_initial TINYINT,
    IN p_is_final_approve TINYINT,
    IN p_is_final_reject TINYINT,
    IN p_is_active TINYINT,
    IN p_created_by_id INT,
    OUT p_id INT)
BEGIN
    DECLARE existing_id INT;
    SELECT id INTO existing_id FROM core_status WHERE code = p_code;
    IF existing_id IS NULL THEN
        INSERT INTO core_status (name, code, description, is_initial, is_final_approve, is_final_reject, is_active, created_by_id, created_at)
        VALUES (p_name, p_code, p_description, p_is_initial, p_is_final_approve, p_is_final_reject, p_is_active, p_created_by_id, NOW());
        SET p_id = LAST_INSERT_ID();
    ELSE
        SET p_id = existing_id;
    END IF;
END
;;
delimiter ;

-- ----------------------------
-- Procedure structure for EnsureTransition
-- ----------------------------
DROP PROCEDURE IF EXISTS `EnsureTransition`;
delimiter ;;
CREATE PROCEDURE `EnsureTransition`(IN p_name VARCHAR(255),
  IN p_org INT,
  IN p_from_status INT,
  IN p_action INT,
  IN p_to_status INT,
  IN p_entity_type INT,
  OUT p_transition_id INT)
BEGIN
  DECLARE v_id INT;
  SELECT id INTO v_id
  FROM core_transition
  WHERE organization_id=p_org AND entity_type_id=p_entity_type
    AND from_status_id=p_from_status AND action_id=p_action AND to_status_id=p_to_status
  LIMIT 1;

  IF v_id IS NULL THEN
    INSERT INTO core_transition(name, entity_type_id, from_status_id, action_id, to_status_id, organization_id, created_at, is_active)
    VALUES (p_name, p_entity_type, p_from_status, p_action, p_to_status, p_org, NOW(), 1);
    SET v_id = LAST_INSERT_ID();
  ELSE
    UPDATE core_transition SET name=p_name, is_active=1 WHERE id=v_id;
  END IF;

  SET p_transition_id = v_id;
END
;;
delimiter ;

SET FOREIGN_KEY_CHECKS = 1;
