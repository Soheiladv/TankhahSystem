classDiagram
direction BT
class node26
class node42
class node10
class node19
class node25
class node20
class node24
class node18
class node39
class node6
class node14
class node56
class node60
class node61
class node4
class node7
class node12
class node31
class node8
class node0
class node30
class node35
class node22
class node45
class node48
class node21
class node47
class node3
class node34
class node2
class node40
class node54
class node16
class node52
class node46
class node9
class node5
class node38
class node32
class node44
class node17
class object
class node53
class node57
class node13
class node55
class node62
class node37
class node23
class node11
class node15
class node27
class node50
class node59
class node43
class node1
class node36
class node49
class node29
class node33
class node58
class node51
class node28

node26 "1" --* "1" node17 
node42 "0..*" --* "1" node25 
node42 "1" --* "1" node17 
node10 "0..*" --* "1" node18 
node10 "1" --* "1" node17 
node19 "0..*" --* "1" node10 
node19 "0..*" --* "1" node18 
node19 "1" --* "1" node17 
node25 "0..*" --* "0..*" node24 : through = 'CustomUserGroup';
node25 "0..*" --* "0..*" node39 
node25 "1" --* "1" node9 
node25 "0..*" --* "0..*" node5 
node25 "0..*" --* "0..*" node38 
node25 "1" --* "1" node32 
node20 "0..*" --* "1" node25 
node20 "0..*" --* "1" node24 
node20 "1" --* "1" node17 
node24 "0..*" --* "0..*" node39 
node24 "1" --* "1" node17 
node18 "1" --* "1" node17 
node39 "0..*" --* "1" node39 
node39 "0..*" --* "0..*" node38 
node39 "1" --* "1" node17 
node6 "1" --* "1" node17 
node14 "0..*" --* "1" node25 
node14 "0..*" --* "1" node60 
node14 "0..*" --* "1" node61 
node14 "0..*" --* "1" node47 
node14 "0..*" --* "1" node54 
node14 "1" --* "1" node17 
node56 "0..*" --* "1" node25 
node56 "0..*" --* "1" node44 
node56 "1" --* "1" node17 
node60 "0..*" --* "1" node61 
node60 "0..*" --* "1" node47 
node60 "1" --* "1" node17 
node61 "0..*" --* "1" node25 
node61 "0..*" --* "1" node47 
node61 "1" --* "1" node17 
node4 "0..*" --* "1" node25 
node4 "0..*" --* "1" node14 
node4 "1" --* "1" node17 
node7 "0..*" --* "1" node61 
node7 "0..*" --* "1" node47 
node7 "1" --* "1" node17 
node12 "0..*" --* "1" node25 
node12 "0..*" --* "1" node14 
node12 "1" --* "1" node17 
node12 "0..*" --* "1" node1 
node31 "0..*" --* "1" node14 
node31 "0..*" --* "1" node47 
node31 "1" --* "1" node17 
node8 "0..*" --* "1" node25 
node8 "1" --* "1" node17 
node0 "0..*" --* "1" node25 
node0 "0..*" --* "1" node8 
node0 "0..*" --* "1" node34 
node0 "1" --* "1" node17 
node0 "0..*" --* "0..*" node11 
node0 "0..*" --* "1" node1 
node30 "0..*" --* "1" node25 
node30 "0..*" --* "1" node14 
node30 "0..*" --* "1" node54 
node30 "0..*" --* "1" node16 
node30 "1" --* "1" node17 
node35 "1" --* "1" node17 
node22 "0..*" --* "1" node25 
node22 "1" --* "1" node17 
node45 "1" --* "1" node17 
node48 "1" --* "1" node17 
node21 "1" --* "1" node17 
node47 "0..*" --* "1" node47 
node47 "0..*" --* "1" node3 
node47 "1" --* "1" node17 
node3 "1" --* "1" node17 
node34 "0..*" --* "1" node47 
node34 "0..*" --* "1" node34 
node34 "1" --* "1" node17 
node2 "0..*" --* "1" node34 
node2 "0..*" --* "1" node46 
node2 "1" --* "1" node17 
node40 "0..*" --* "1" node25 
node40 "0..*" --* "1" node34 
node40 "1" --* "1" node17 
node54 "0..*" --* "0..*" node47 
node54 "1" --* "1" node17 
node16 "0..*" --* "0..*" node30 
node16 "0..*" --* "1" node54 
node16 "1" --* "1" node17 
node52 "0..*" --* "1" node25 
node52 "0..*" --* "1" node34 
node52 "1" --* "1" node17 
node46 "1" --* "1" node17 
node5 "0..*" --* "0..*" node38 
node5 "1" --* "1" node17 
node38 "0..*" --* "1" node44 
node38 "1" --* "1" node17 
node32 "0..*" --* "0..*" node5 
node32 "0..*" --* "0..*" node38 
node32 "1" --* "1" node17 
node44 "1" --* "1" node17 
node17 "1" --* "1" object 
node53 "1" --* "1" node17 
node53 "1" --* "1" node1 
node57 "1" --* "1" node17 
node13 "1" --* "1" node17 
node55 "1" --* "1" node17 
node62 "1" --* "1" node17 
node37 "0..*" --* "1" node25 
node37 "0..*" --* "1" node34 
node37 "0..*" --* "1" node46 
node37 "1" --* "1" node17 
node37 "0..*" --* "1" node11 
node37 "0..*" --* "1" node27 
node37 "0..*" --* "1" node1 
node23 "1" --* "1" node17 
node11 "0..*" --* "0..*" node25 
node11 "0..*" --* "1" node46 
node11 "1" --* "1" node17 
node11 "0..*" --* "1" node1 
node15 "1" --* "1" node17 
node15 "0..*" --* "1" node11 
node27 "0..*" --* "1" node22 
node27 "1" --* "1" node17 
node27 "0..*" --* "1" node11 
node50 "0..*" --* "1" node25 
node50 "1" --* "1" node17 
node50 "0..*" --* "1" node1 
node59 "0..*" --* "1" node34 
node59 "0..*" --* "1" node46 
node59 "1" --* "1" node17 
node43 "1" --* "1" node17 
node1 "0..*" --* "1" node25 
node1 "0..*" --* "0..*" node25 
node1 "0..*" --* "1" node14 
node1 "0..*" --* "1" node47 
node1 "0..*" --* "1" node34 
node1 "0..*" --* "1" node54 
node1 "0..*" --* "1" node16 
node1 "0..*" --* "1" node46 
node1 "1" --* "1" node17 
node36 "0..*" --* "1" node25 
node36 "0..*" --* "1" node22 
node36 "0..*" --* "1" node34 
node36 "0..*" --* "1" node46 
node36 "1" --* "1" node17 
node36 "0..*" --* "1" node1 
node49 "1" --* "1" node17 
node49 "0..*" --* "1" node1 
node29 "1" --* "1" node17 
node33 "1" --* "1" node17 
node33 "0..*" --* "1" node33 
node58 "1" --* "1" node17 
node58 "0..*" --* "1" node33 
node51 "1" --* "1" node17 
node51 "0..*" --* "1" node33 
node28 "1" --* "1" node17 
node28 "0..*" --* "0..*" node33 
