// convenience function to create icon
function create_marker_icon(type) {
  icon = new GIcon();
  icon.image = '/static/images/large_active_marker.png';
  if (type == 'buoy') {
    icon.image = '/static/images/large_active_marker.png';
  }
  icon.shadow = null;
  icon.iconSize = new GSize(23, 23);
  icon.shadowSize = null;
  icon.iconAnchor = new GPoint(11, 11);
  icon.infoWindowAnchor = new GPoint(11, 11); 
  return icon;
}

// Create a buoy or spot icon
function create_marker(type, position, title) {
  icon = create_marker_icon(type);
  return new GMarker(position, {title:title, icon:icon});
}

// Create basic map and add the appropriate primary marker (buoy or spot)
function initialize(lat, long, title, type) {
  if (GBrowserIsCompatible()) {
    var map = new GMap2(document.getElementById("map_canvas"));
    map.setCenter(new GLatLng(lat, long), 13);
    map.setUIToDefault();
  }
  var spotPos = new GLatLng(lat, long);
  marker = create_marker(type, spotPos, title);
  map.addOverlay(marker);
}
