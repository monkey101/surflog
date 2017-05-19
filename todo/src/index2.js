<html>
  <head>
    <script src="https://s3.amazonaws.com/baas-sdks/js/library/b857841a7dfdce6da579166934f3e214210e0267/baas.min.js" type="text/javascript"></script>
    <script src="https://code.jquery.com/jquery-3.1.1.min.js" integrity="sha256-hVVnYaiADRTO2PzUGmuLJr8BLUSjGIZsDYGmIJLv2b8=" crossorigin="anonymous"></script>
  </head>
  <body>

    <!--  Auth Links  -->
    <a href="#" class="login-link" id="facebook-login">log in with facebook</a>
    <a href="#" class="login-link" id="google-login">log in with google</a>
    <a href="#" class="login-link" id="anonymous-login">log in anonymously</a>
    <a href="#" id="logout" >log out</a>

    <div class="content">
      <div id="greeting"></div>
      <textarea id="note" placeholder="you can save some data here."></textarea>
      <button id="save">Save</button>
    </div>

  </body>

  <script type="text/javascript">
    // Set these values to match the ID of the app you created in the BaaS admin site (Clients page) and
    // the DB of the default rule created in the mongodb1 service (Rules tab).
    var MY_APP_ID = "surflog-kapys";
    var MY_DB = "helloworld";

    var baasClient = new baas.BaasClient(MY_APP_ID);
    function setupPage() {
      var userInfo = baasClient.auth();

      if(userInfo){
        $(".login-link").hide()
        $("#logout").show().click(function(){
          baasClient.logout().then(function(){
            setupPage();
          });
        });
        var userName = (userInfo.user.data && userInfo.user.data.name)  ? userInfo.user.data.name : "(unknown)";
        $("#greeting").text("Hello " + userName + ",  you are logged in!");

        var db = baasClient.service("mongodb", "mongodb1").db(MY_DB);

        db.collection("items").find({owner_id: baasClient.authedId()}, {})
          .then(function(data){
              if(data.length !== 0){
                $('#note').val(data[0].note);
              }
          });
        $("#save").click(function(){
          db.collection("items").updateOne({owner_id: baasClient.authedId()}, {$set:{"note":$("#note").val()}}, {upsert: true});
        })
        return;
      }

      $(".content").hide();
      $("#logout").hide();
      $("#facebook-login").show().click(function(){
        baasClient.authWithOAuth("facebook")
      });
      $("#google-login").show().click(function(){
        baasClient.authWithOAuth("google")
      });
      $("#anonymous-login").show().click(function(){
        baasClient.anonymousAuth(true).then(()=>{
          window.location.replace("/")
        });
      });
    }

    $(document).ready(setupPage);
  </script>
</html>
