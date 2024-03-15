ymaps.ready(init);

function init() {

    var latitude   = document.querySelector("#map").getAttribute("latitude");
    var longtitude = document.querySelector("#map").getAttribute("longtitude");
    var zoom       = document.querySelector("#map").getAttribute("zoom");

    var myMap = new ymaps.Map("map", {
            center: [latitude, longtitude],
            zoom: zoom
        }, {
            searchControlProvider: 'yandex#search'
    });

    myMap.geoObjects.removeAll();
    myMap.geoObjects.add(new ymaps.Placemark([latitude, longtitude], {
        balloonContent: 'Here'
    }, {
        preset: 'islands#icon',
        iconColor: '#0095b6'
    }));

    myMap.events.add('click', function (e) {
        var coords = e.get('coords');        
        latitude = document.querySelector("#id_latitude");
        latitude.value = coords[0].toPrecision(6);
        longtitude = document.querySelector("#id_longtitude");
        longtitude.value = coords[1].toPrecision(6);
        zoom = document.querySelector("#id_zoom");
        zoom.value = Number(myMap._zoom);

        myMap.geoObjects.removeAll();
        myMap.geoObjects.add(new ymaps.Placemark([latitude.value, longtitude.value], {
            balloonContent: 'Here'
        }, {
            preset: 'islands#icon',
            iconColor: '#0095b6'
        }));

    });
}
