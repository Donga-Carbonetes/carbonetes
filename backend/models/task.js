
const { DataTypes } = require("sequelize");
const sequelize = require("../config/db");

const Task = sequelize.define("Task", {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true,
  },
  task_name: {
    type: DataTypes.STRING,
    allowNull: true,  // null 허용
  },
  taskname_user: {
    type: DataTypes.STRING,
  },
  data_shape: {
    type: DataTypes.STRING,
  },
  dataset_size: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  label_count: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  cluster_name: {
    type: DataTypes.STRING,
  },
  created_at: {
    type: DataTypes.DATE,
  },
  dispatched_at: {
    type: DataTypes.DATE,
  },
  completed_at: {
    type: DataTypes.DATE,
  },
  status: {
    type: DataTypes.STRING,
  },
  estimated_time: {
    type: DataTypes.INTEGER,
  },
}, {
  tableName: "task_info",
  timestamps: false,
});

module.exports = Task;

  
