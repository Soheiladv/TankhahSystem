          

-- ----------------------------
-- Table structure for version_tracker_finalversion
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_finalversion`;
CREATE TABLE `version_tracker_finalversion`  (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `version_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `release_date` datetime(6) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  INDEX `version_tracker_finalversion_release_date_c20ebe81`(`release_date` ASC) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of version_tracker_finalversion
-- ----------------------------
INSERT INTO `version_tracker_finalversion` VALUES (1, '6.0.0.166', '2025-04-04 18:15:17.084415', 1);

-- ----------------------------
-- Table structure for version_tracker_finalversion_app_versions
-- ----------------------------
DROP TABLE IF EXISTS `version_tracker_finalversion_app_versions`;
CREATE TABLE `version_tracker_finalversion_app_versions`  (
  `id` int NOT NULL AUTO_INCREMENT,
  `finalversion_id` bigint NOT NULL,
  `appversion_id` bigint NOT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `version_tracker_finalver_finalversion_id_appversi_e7a4bca7_uniq`(`finalversion_id` ASC, `appversion_id` ASC) USING BTREE,
  INDEX `version_tracker_fina_appversion_id_8323129b_fk_version_t`(`appversion_id` ASC) USING BTREE,
  CONSTRAINT `version_tracker_fina_appversion_id_8323129b_fk_version_t` FOREIGN KEY (`appversion_id`) REFERENCES `version_tracker_appversion` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `version_tracker_fina_finalversion_id_65306579_fk_version_t` FOREIGN KEY (`finalversion_id`) REFERENCES `version_tracker_finalversion` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 618 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of version_tracker_finalversion_app_versions
-- ----------------------------
INSERT INTO `version_tracker_finalversion_app_versions` VALUES (617, 1, 2423);

SET FOREIGN_KEY_CHECKS = 1;
