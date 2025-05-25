// socket.js
let io;

module.exports = {
  init: (server) => {
    const { Server } = require("socket.io");
    io = new Server(server, {
      cors: {
        origin: "http://localhost:3000", // 프론트 주소
        methods: ["GET", "POST"]
      }
    });

    io.on("connection", (socket) => {
      console.log("🛰️ 소켓 연결됨:", socket.id);
    });

    return io;
  },

  getIO: () => {
    if (!io) {
      throw new Error("Socket.io가 아직 초기화되지 않았습니다.");
    }
    return io;
  },
};
