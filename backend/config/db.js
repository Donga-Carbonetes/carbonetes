const { Sequelize } = require("sequelize");
require("dotenv").config(); // .env 파일에서 환경 변수 로딩

// Sequelize 인스턴스 생성: DB 연결 설정
const sequelize = new Sequelize(
  process.env.DB_NAME,     // DB 이름
  process.env.DB_USER,     // 사용자
  process.env.DB_PASSWORD, // 비밀번호
  {
    host: process.env.DB_HOST,  // DB 호스트
    port: process.env.DB_PORT, // 포트
    dialect: "mysql", // MySQL 사용
    logging: false, // SQL 로그 false
  }
);


module.exports = sequelize;
