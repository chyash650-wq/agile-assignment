import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
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

window.addEventListener("load", function () {

  document.getElementById("login").addEventListener("click", function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    signInWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        userCredential.user.getIdToken().then((token) => {
          document.cookie = "token=" + token + ";path=/";
          window.location = "/";
        });
      })
      .catch((error) => console.log(error.message));
  });

  document.getElementById("signup").addEventListener("click", function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    createUserWithEmailAndPassword(auth, email, password)
      .then((userCredential) => {
        userCredential.user.getIdToken().then((token) => {
          document.cookie = "token=" + token + ";path=/";
          window.location = "/";
        });
      })
      .catch((error) => console.log(error.message));
  });

  document.getElementById("logout").addEventListener("click", function () {
    signOut(auth).then(() => {
      document.cookie = "token=;path=/";
      window.location = "/";
    });
  });

});