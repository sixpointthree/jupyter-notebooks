var p = new Promise(function(resolve, reject) {
    setTimeout(function() {
        resolve("Hallo Welt");
    }, 2000);
})

p.then(function(a) {
    console.log(a);
})