
function draw() {
	var config = {
        container_id: "viz",
        server_url: "bolt://192.168.23.91:7676",
        server_user: "neo4j",
	server_password: "test",
        labels: {
            "Term": {
                 "name": "name",
                 "expert": "expert"
            }
        },
        relationships: {
            "USING_FOR": {
                "from_": "from_",
                "to_": "to_"
            },
            "IS_CAUSE_OF": {
                "from_": "from_",
                "to_": "to_"
            }
        },
        initial_cypher: "MATCH (n)-[r]->(m) RETURN n,r,m"
   }   
   var viz = new NeoVis.default(config);
   viz.render();
   console.log(viz);
}
        
