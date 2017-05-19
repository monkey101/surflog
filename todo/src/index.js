import React from 'react';
import { render } from 'react-dom';
import { BaasClient } from 'baas';
import { browserHistory, Route } from 'react-router'
import { BrowserRouter, Link } from 'react-router-dom'

require("../static/todo.scss")

let appId = 'surflog-kapys';
if (process.env.APP_ID) {
  appId = process.env.APP_ID;
}

let options = {};
if (process.env.BAAS_URL) {
  options.baseUrl = process.env.BAAS_URL;
}

let baasClient = new BaasClient(appId, options);
let db = baasClient.service("mongodb", "surflog").db("surf_log")
let buoys = db.collection("buoys")
let users = db.collection("users")

// BUOY
let Buoy = class extends React.Component {

	render() {
		return (
			<div className="todo-item-root">
				<label className="todo-item-container">
					<span className="todo-item-text">
                        <Link to={{pathname: `/buoy/${this.props.item._id}`, query: this.props.item._id}}>{this.props.item._id} - {this.props.item.description}</Link>
                    </span>
				</label>
			</div>
		)
	}
}

// BUOY DETAIL
let BuoyDetail = class extends React.Component {

    constructor(props) {
        super(props);
    }

	render() {
        let buoy = null
        console.log("buoyId: " + this.props.match.params.buoyId)
        let authed = baasClient.auth() != null
        if(!authed){
          console.log("Not authed")
          return null
        }

        buoys.find({"_id" : this.props.match.params.buoyId}).then((data) => {
            if (data.length == 0){
                console.log("ERROR: buoy not found")
                document.getElementById("resultFound").innerHTML = "Result not found";
            } else {
                buoy = data[0]
                console.log(buoy.description)
                console.log(data[0])
            }
        }).catch ( err => {
            console.error("error in search!", err);
        });
        return ( <div>{buoy.description}</div> )  
    }
}

// AUTH CONTROLS
var AuthControls = class extends React.Component {

  render() {
    let authed = this.props.client.auth() != null
    let logout = () => this.props.client.logout().then(() => location.reload());
    let userData = null
    if(baasClient.auth() && baasClient.auth().user){
      userData = baasClient.auth().user.data
    }
    return (
      <div>
        { authed ?
          (
            <div className="login-header">
              {userData && userData.picture ?
                <img src={userData.picture} className="profile-pic"/>
                : null
              }
              <span className="login-text">
                <span className="username">{userData && userData.name ? userData.name : "?"}</span>
              </span>
              <div>
                <a className="logout" href="#" onClick={() => logout()}>sign out</a>
              </div>
              <div>
                <a className="settings" href="/settings">settings</a>
              </div>
            </div>
          ) : null
        }
        {	!authed ?
            <div className="login-links-panel">
                <h2>Surf Log</h2>
                <div onClick={() => this.props.client.authWithOAuth("google")} className="signin-button">
                    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="18px" height="18px" viewBox="0 0 48 48">
                        <g>
                            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"></path>
                            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"></path>
                            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"></path>
                            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"></path>
                            <path fill="none" d="M0 0h48v48H0z"></path>
                        </g>
                    </svg>
                    <span className="signin-button-text">Sign in with Google</span>
                </div>
                <div onClick={() => this.props.client.authWithOAuth("facebook")} className="signin-button">
                <div className="facebook-signin-logo"></div>
                    <span className="signin-button-text">Sign in with Facebook</span>
                </div>
            </div>
            : null
        }
      </div>
    )
  }
}

// BUOY LIST
var BuoyList = class extends React.Component {

  loadList() {
    let authed = baasClient.auth() != null
    if(!authed){
      return
    }
    let obj = this;
    buoys.find(null, null).then(function(data){
      obj.setState({ buoys:data })
    }).catch(err => {
        console.log(err)
        this.setState({ err })
    })
  }

  constructor(props) {
    super(props);

    this.state = {
      buoys: []
    };
  }

  componentWillMount() {
    this.loadList();
  }

  componentDidMount(){
    this.loadList()
  }

  clear() {
    buoys.deleteMany().then(() => {
      this.loadList();
    })
  }

  render() {
    let loggedInResult =
      (<div>
         <div className="controls">
            Buoy Listing:
         </div>
         { this.state.err ? <strong>{this.state.err.toString()}</strong> : <div></div> }
         <ul className="items-list">
         {
           this.state.buoys.length == 0
             ?  <div className="list-empty-label">empty list.</div>
             : this.state.buoys.map((item) => {
               return <Buoy key={item._id.toString()} item={item} onChange={() => this.loadList()} />;
          })
        }
        </ul>
      </div>);
    return baasClient.auth() == null ? null : loggedInResult;
  }
}

// HOME
var Home = function(){
  let authed = baasClient.auth() != null
  return (
    <div>
      <AuthControls client={baasClient}/>
      <BuoyList/>
    </div>
  )
}

// SETTINGS
var Settings = class extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      user: null
    };
  }

  loadUser() {
    users.find({}, null).then((data)=>{
      if(data.length>0){
        this.setState({user:data[0]})
      }
    })
  }

  componentWillMount() {
    this.loadUser();
  }

  render() {
    return (
      <div>
        <Link to="/">Buoys</Link>
        {
         ((u) => {
              if(u != null){
                if(u.number_status==="pending"){
                  return <AwaitVerifyCode onSubmit={() => this.loadUser()}/>
                } else if(u.number_status==="verified"){
                  return (<div>{`Your number is verified, and it's ${u.phone_number}`}</div>)
                }
              }
            })(this.state.user)
        }
      </div>
    )
  }
}

// MAIN
render((
  <BrowserRouter>
    <div>
      <Route exact path="/" component={Home}/>
      <Route path="/settings" component={Settings}/>
      <Route path="/buoy/:buoyId" component={BuoyDetail}/>
    </div>
  </BrowserRouter>
), document.getElementById('app'))
