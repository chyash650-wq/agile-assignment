import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAYeNarnXgDbs0jflSB1Y3MV7M-5mtG-m4",
  authDomain: "room-schedulerr.firebaseapp.com",
  projectId: "room-schedulerr",
  storageBucket: "room-schedulerr.firebasestorage.app",
  messagingSenderId: "186144798485",
  appId: "1:186144798485:web:ed1227609cc68c33abdb1c"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

function setToken(userCredential) {
  return userCredential.user.getIdToken().then((token) => {
    document.cookie = "token=" + token + ";path=/";
    window.location.href = "/dashboard";
  });
}

window.onload = function () {
  document.getElementById("login").onclick = function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    signInWithEmailAndPassword(auth, email, password)
      .then(setToken)
      .catch((error) => window.showError(error.message));
  };

  document.getElementById("signup").onclick = function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    createUserWithEmailAndPassword(auth, email, password)
      .then(setToken)
      .catch((error) => window.showError(error.message));
  };
};