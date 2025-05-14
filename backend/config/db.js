const { Sequelize } = require("sequelize");
require("dotenv").config(); // .env 읽기

const sequelize = new Sequelize(
  process.env.DB_NAME,     // DB 이름
  process.env.DB_USER,     // 사용자
  process.env.DB_PASSWORD, // 비밀번호
  {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    dialect: "mysql",
    logging: false, // SQL 로그 false
  }
);


module.exports = sequelize;
