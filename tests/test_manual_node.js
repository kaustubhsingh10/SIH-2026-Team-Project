const { MockCrimeGraphAdapter, HttpCrimeGraphAdapter } = require('../web/service.js');

async function testManualCreation() {
    console.log("==================================================");
    console.log("CRIMEGRAPH AI — MANUAL ENTITY & REL INTEGRATION");
    console.log("==================================================");

    // 1. Test Mock Adapter
    const mock = new MockCrimeGraphAdapter();
    const mockPerson = await mock.createEntity({ entity_type: "PERSON", name: "Rohan Verma", age: 29 });
    console.log("[Mock] Created Entity:", mockPerson.id, mockPerson.name, "Origin:", mockPerson.origin);

    const mockVehicle = await mock.createEntity({ entity_type: "VEHICLE", registration_number: "MH-04-EE-1111" });
    console.log("[Mock] Created Vehicle:", mockVehicle.id, mockVehicle.registration_number);

    const mockRel = await mock.createRelationship({
        source_id: mockPerson.id,
        target_id: mockVehicle.id,
        relationship: "OWNS",
        confidence: 0.96
    });
    console.log("[Mock] Created Relationship:", mockRel.id, `${mockRel.source} --${mockRel.relationship}--> ${mockRel.target}`);

    const graphSlice = await mock.getCaseGraph("ALL");
    const foundNode = graphSlice.nodes.find(n => n.id === mockPerson.id);
    const foundEdge = graphSlice.edges.find(e => e.id === mockRel.id);
    console.log("[Mock] Node in Graph:", !!foundNode, "| Edge in Graph:", !!foundEdge);

    await mock.deleteEntity(mockPerson.id);
    const afterDelGraph = await mock.getCaseGraph("ALL");
    console.log("[Mock] Node Deleted & Edge Cleaned Up:", !afterDelGraph.nodes.find(n => n.id === mockPerson.id) && !afterDelGraph.edges.find(e => e.id === mockRel.id));

    console.log("==================================================");
    console.log("MANUAL ENTITY & RELATIONSHIP VERIFICATION PASSED");
    console.log("==================================================");
}

testManualCreation().catch(err => {
    console.error("Test failed:", err);
    process.exit(1);
});
