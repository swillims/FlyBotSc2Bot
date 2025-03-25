from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId as uId
from sc2.data import Race, Result

from sc2.units import Units

# NOTE: bot uses a mix of len() and .amount. I did not realize .amount exists earlier and too much dev time to change something that also works

class flyBot(BotAI):

    async def on_start(self) :
        self.trainingBlock = False
        self.gateWayBlock = False
        self.starGateBlock = False
        self.earlyDone = False
        self.midDone = False
        self.hasBeenAttacked = False
        self.zealotPlus = 0
        self.stalkerPlus = 0
        self.phoenixPlus = 0
        self.voidRayPlus = 0
        self.rallyPointDefend = self.start_location.towards(self.enemy_start_locations[0],10)
        try:
            self.rallyPointDefend = self.main_base_ramp.top_center.towards(self.start_location,2)
        except:
            print("ramp sad")
        self.pathingLocationCheck = await self.find_placement(uId.PYLON, near=self.game_info.map_center)
        for n in self.structures(uId.NEXUS):
            n.train(uId.PROBE)
        if self.enemy_race == Race.Random:
            self.stalkerPlus = 0
            self.voidRayPlus = 1
            self.enemFaction = Race.Random
        elif self.enemy_race == Race.Terran:
            self.stalkerPlus = 0
            self.voidRayPlus = 1
            self.enemFaction = Race.Terran
        elif self.enemy_race == Race.Zerg:
            self.stalkerPlus = 0
            self.voidRayPlus = 2 # voidray is more optimal than phoenix into early zerg defensively. Can only lift once into zergling(1/2 supply) once. Roach is armored.
            self.enemFaction = Race.Zerg
        elif self.enemy_race == Race.Protoss:
            self.stalkerPlus = 0
            self.voidRayPlus = 1
            self.enemFaction = Race.Protoss
    async def on_step(self, iteration):
        self.quarry()
        await self.fixWorkers() # testing
        if self.earlyDone == False: # 4 minutes? The math is weird
            await self.buildOrder()
            if iteration%10==1:
                pass#await self.distribute_workers()
            if iteration%10==3:
                await self.proximityDefend()
            if iteration%10==5:
                await self.rally()
            if iteration%10==7:
                await self.adjustEnemy()
        elif self.midDone == False:
            if iteration % 10 == 1:
                await self.handleTrappedUnits()
            elif iteration % 10 == 2:
                await self.nexusLogic()
            elif iteration % 10 == 3:
                await self.manageSupply()
            elif iteration % 10 == 4:
                await self.starGateLogic(num=3,oNum=1,pNum=self.phoenixPlus,vNum=self.voidRayPlus)
            elif iteration % 10 == 5:
                await self.gateWayLogic(num=2,supplyStop=150)
            elif iteration % 10 == 6:
                await self.fleetBeaconLogic()
                await self.adjustEnemy()
            elif iteration % 10 == 7:
                await self.cCoreLogic()
                await self.oracleEarlyScout()
            elif iteration % 10 == 8:
                await self.proximityDefend()
            elif iteration % 10 == 9:
                await self.rally()
            elif iteration % 10 == 0:
                await self.scout()
                await self.lateGameCheck()
        else:
            if iteration % 20 == 1:
                pass#await self.distribute_workers()
            elif iteration % 20 == 2:
                await self.nexusLogic()
            elif iteration % 20 == 3:
                await self.manageSupply()
            elif iteration % 20 == 4:
                #p = len(self.quarryUnits(uId.PHOENIX))
                #v = len(self.quarryUnits(uId.VOIDRAY))
                await self.starGateLogic(num=5,oNum=1,pNum=self.phoenixPlus,vNum=self.voidRayPlus)
            elif iteration % 20 == 5:
                await self.gateWayLogic(supplyStop=175)
            elif iteration % 20 == 6:
                await self.fleetBeaconLogic()
            elif iteration % 20 == 7:
                await self.cCoreLogic()
            elif iteration % 20 == 8:
                await self.proximityDefend()
            elif iteration % 20 == 9:
                await self.scout()
            elif iteration % 20 == 10:
                await self.rally()
            elif iteration % 20 == 11:
                await self.forgeLogic()
            elif iteration % 20 == 12:
                await self.powerUnpowered()
            elif iteration % 20 == 13:
                await self.handleTrappedUnits()
            elif iteration % 20 == 14:
                await self.adjustEnemy()
            # is derived from army command at % 20 == 0 to be make army alternate between condensing and attacking for better micro
            # is separate from other iteration checks to make changes quicker and less complicated
            elif iteration % 20 == 2:
                if self.notSafeUnit.exists or self.quarryEnemyStructure.exists:
                    ex = [uId.PROBE]
                    if self.supply_used<180:
                        ex.append(uId.ORACLE)
                    await self.armyWaitGroup(exclude=ex)
        # things I want running every game step
        await self.probeMicro()
        await self.stalkerMicro()
        await self.phoenixMicro()
        await self.oracleMicro()
        await self.tempestMicro()
        await self.voidRayMicro()
        await self.motherShipMicro()
    async def on_end(self, game_result: Result):
        print("Unit Comp Adjustment Math Numbers")
        print("zealotPlus")
        print(self.zealotPlus)
        print("stalkerPlus")
        print(self.stalkerPlus)
        print("phoenixPlus")
        print(self.phoenixPlus)
        print("voidRayPlus")
        print(self.voidRayPlus)
    ## helper functions
    def quarry(self):  # I borrowed this from another hobby bot I did because it saves a lot of time. It serves three purposes. It marginally improves performance, it makes not overreacting to situations easier, and it makes other sections of code more readable.
        self.quarryUnits = self.units.not_structure
        self.quarryStructures = self.structures.exclude_type(uId.ORACLESTASISTRAP)
        self.quarrySelf = self.quarryUnits | self.quarryStructures
        self.workerNotBuilding = self.quarryUnits(uId.PROBE).idle | self.quarryUnits(uId.PROBE).filter(lambda pr: checkMultiOrder(pr,[AbilityId.HARVEST_GATHER,AbilityId.HARVEST_RETURN,AbilityId.MOVE]))
        self.workerBuilder = self.workerNotBuilding
        wb = self.workerBuilder.filter(lambda wbwb: not wbwb.is_carrying_resource)
        if wb.exists:
            self.workerBuilder = wb
        self.quarryEnemyUnit = self.enemy_units.not_structure.exclude_type(uId.LARVA).exclude_type(uId.EGG).exclude_type(uId.MULE)
        self.quarryEnemyStructure = self.enemy_structures
        self.quarryEnemy = self.quarryEnemyUnit | self.quarryEnemyStructure
        self.notSafeUnit = self.quarryEnemyUnit.exclude_type(uId.SCV).exclude_type(
            uId.DRONE).exclude_type(uId.PROBE).exclude_type(uId.CHANGELING).exclude_type(
            uId.CHANGELINGMARINESHIELD).exclude_type(uId.CHANGELINGMARINE).exclude_type(
            uId.OVERLORD).exclude_type(uId.OVERSEER).exclude_type(uId.OBSERVER)
        self.quarryEnemyAttackAir = self.quarryEnemy.filter(lambda e: e.can_attack_air)
        self.avoidObstacle = self.mineral_field | self.vespene_geyser

    # base macro
    async def buildOrder(self):
        pr = self.workerNotBuilding
        n = self.quarryStructures(uId.NEXUS)
        pl = self.quarryStructures(uId.PYLON)
        g = self.quarryStructures(uId.GATEWAY)
        a = self.quarryStructures(uId.ASSIMILATOR)
        c = self.quarryStructures(uId.CYBERNETICSCORE)
        if not self.trainingBlock:
            for nn in n:
                if nn.is_idle:
                    if self.can_afford(uId.PROBE):
                        nn.train(uId.PROBE)
                elif nn.energy >= 50 and not nn.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                    nn(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nn) # It doesn't look like this breaks the game
        #self.trainingBlock = False
        if pr.exists:
            if not pl.exists:
                if not self.already_pending(uId.PYLON) and self.can_afford(uId.PYLON):
                    p = self.start_location
                    try:
                        p = list(self.main_base_ramp.corner_depots)[0]# depot and pylon are both 2x2 in size
                    except:
                        p = await self.find_placement(uId.PYLON,near=self.rallyPointDefend)
                    # p is convoluted because the silly head api maker decided to make corner depots a set instead of a list.
                    prpr = self.workerBuilder.closest_to(p).build(uId.PYLON,p)
                    self.trainingBlock = False
                elif self.supply_used > 14:
                    self.trainingBlock = True
            elif pl.ready.exists:
                if not g.exists:
                    if not self.already_pending(uId.GATEWAY) and self.can_afford(uId.GATEWAY):
                        p = self.start_location
                        try:
                            p = self.main_base_ramp.barracks_correct_placement.position # gateway has same dimensions as barracks
                        except:
                            p = await self.find_placement(uId.GATEWAY, near=self.rallyPointDefend)
                        self.workerBuilder.closest_to(p).build(uId.GATEWAY, p)
                        self.trainingBlock = False
                    elif self.supply_used > 16:
                        self.trainingBlock = True
                elif g.exists:
                    if not self.trainingBlock:
                        for gg in g.ready.idle:
                            if self.can_afford(uId.STALKER):
                                gg.train(uId.STALKER)
                            elif self.can_afford(uId.ZEALOT):
                                gg.train(uId.ZEALOT)
                    if not a.exists:
                        if self.can_afford(uId.ASSIMILATOR) and not self.already_pending(uId.ASSIMILATOR):
                            v = self.vespene_geyser.closer_than(15.0, n.closest_to(self.start_location).position)
                            for vv in v:
                                if not a.closer_than(1, vv).exists:
                                    self.workerBuilder.closest_to(vv).build(uId.ASSIMILATOR, vv)
                                    self.trainingBlock = False
                                    break
                        elif self.supply_used > 18:
                            self.trainingBlock = True
                    if not c.exists and g.ready.exists:
                        if self.can_afford(uId.CYBERNETICSCORE) and not self.already_pending(uId.CYBERNETICSCORE):
                            p = await self.find_placement(uId.CYBERNETICSCORE, near=self.start_location)
                            while p.distance_to(self.rallyPointDefend)<5:
                                p = await self.find_placement(uId.CYBERNETICSCORE, near=self.start_location)
                            self.workerBuilder.closest_to(p).build(uId.CYBERNETICSCORE,p)
                            self.trainingBlock = False
                        elif self.supply_used > 20:
                            self.trainingBlock = True
                    if a.exists and g.ready.exists:
                        if len(n)==1:
                            if self.can_afford(uId.NEXUS) and not self.already_pending(uId.NEXUS):
                                #await self.expand_now()
                                p = await self.get_next_expansion()
                                self.workerBuilder.closest_to(p).build(uId.NEXUS,p)
                                self.trainingBlock = False
                        elif len(n)<2:
                            self.trainingBlock = True
                        elif len(n)==2:
                            if self.can_afford(uId.ASSIMILATOR) and not self.already_pending(uId.ASSIMILATOR):
                                v = self.vespene_geyser.closer_than(15.0, n.closest_to(self.start_location).position)
                                for vv in v:
                                    if not a.closer_than(1, vv).exists:
                                        self.workerBuilder.closest_to(vv).build(uId.ASSIMILATOR, vv)
                                        self.trainingBlock = False
                                        break
                            elif self.supply_used > 21:
                                self.trainingBlock = True
                            if len(pl)<2:
                                if not self.already_pending(uId.PYLON) and self.can_afford(uId.PYLON):
                                    await self.build(uId.PYLON,near=n.random)
                                    self.trainingBlock = False
                                elif self.supply_used > 22:
                                    self.trainingBlock = True
                            elif len(pl)==2:
                                if not self.already_pending(uId.STARGATE) and self.can_afford(uId.STARGATE):
                                    p = await self.findBuildingLocationFixer()
                                    p = await self.find_placement(uId.STARGATE, near=p)
                                    if not p is None:
                                        wb = self.workerBuilder.closest_to(p)
                                        wb.build(uId.STARGATE, p)
                                        await self.build(uId.STARGATE,p)
                                        self.earlyDone = True
                                        self.trainingBlock = False
                                elif self.supply_used > 24:
                                    self.trainingBlock = True

    async def manageSupply(self, supplyBuffer=8, structureHops=8, obstacleHops=8, preHop=1):
        n = self.quarryStructures(uId.NEXUS)
        #pr = self.workerNotBuilding
        if n.exists and self.workerBuilder.exists:
            if(not self.quarryStructures(uId.PYLON).exists)or(self.supply_left<supplyBuffer and self.supply_cap<200):
                if not self.already_pending(uId.PYLON):
                    p = self.quarryStructures(uId.NEXUS).furthest_to(self.start_location).position
                    if self.avoidObstacle.exists:
                        p = p.towards(self.pathingLocationCheck,preHop)
                        for i in range(obstacleHops):
                            p = p.towards(self.avoidObstacle.closest_to(p),-1)
                        p = p.towards(self.pathingLocationCheck, preHop)
                        for i in range(structureHops):
                            p = p.towards(self.quarryStructures.closest_to(p), -1)
                    p = await self.find_placement(uId.PYLON, near=p)
                    self.workerBuilder.closest_to(p).build(uId.PYLON,p)

    async def nexusLogic(self, motherShip=True, baseCap=3, supplyMin=90,mineralSupplyOverride=500,extraBaseSurplus=800):
        n = self.quarryStructures(uId.NEXUS)
        nm = n.ready # going to check for nearby mineral later
        m = self.mineral_field
        pr = self.quarryUnits(uId.PROBE)
        self.trainingBlock = False
        for e in self.quarryEnemyStructure: # structure not unit
            for mm in m.closer_than(15,e):
                if mm in m:
                    m.remove(mm)
        for nn in n.ready:
            if len(m.closer_than(9,nn))<5:
                nm.remove(nn)
        if pr.exists:
            if len(nm)>0 and self.minerals<mineralSupplyOverride:
                if self.supply_used < supplyMin:
                    baseCap = 2
                if self.minerals > extraBaseSurplus:
                    baseCap += 1
                #x = len(self.quarryStructures(uId.GATEWAY).ready | self.quarryStructures(uId.STARGATE).ready)
                #if x <= len(nm):
                #    cap = x
            if m.exists and len(nm)<baseCap:
                if len(pr)>len(nm)*15:
                    if not self.already_pending(uId.NEXUS):
                        if self.can_afford(uId.NEXUS):
                            #await self.expand_now()
                            p = await self.findExpandLocation()
                            if self.workerNotBuilding.exists and not p is None:
                                b = self.workerNotBuilding.closest_to(p)
                                if await self.client.query_pathing(b,p) is None:
                                    b = self.workerNotBuilding.furthest_to(b)
                                b.build(uId.NEXUS, p)
                            if not self.hasBeenAttacked:
                                self.rallyPointDefend = self.quarryStructures.closest_to(self.pathingLocationCheck).position.towards(self.pathingLocationCheck,4)
                        else:
                            self.trainingBlock = True
            for nn in n.idle:
                if nm.exists and len(pr)<len(nm)*20 and len(pr)<60:
                    if self.can_afford(uId.PROBE):
                        nn.train(uId.PROBE)
            for nn in n:
                v = self.vespene_geyser.closer_than(9,nn)
                for vv in v:
                    if not self.quarryStructures(uId.ASSIMILATOR).closer_than(.5,vv).exists:
                        if self.can_afford(uId.ASSIMILATOR) and not self.already_pending(uId.ASSIMILATOR):
                            if self.workerBuilder.exists:
                                wb = self.workerBuilder.closest_to(vv)
                                wb.build(uId.ASSIMILATOR, vv)
            ne = self.quarryStructures(uId.NEXUS).ready.filter(lambda s: s.energy >= 50)
            b = (self.quarryStructures(uId.STARGATE) | self.quarryStructures(uId.GATEWAY)).ready.filter(lambda s: s.orders and not s.has_buff(BuffId.CHRONOBOOSTENERGYCOST))
            # ^^^ This mess is why I avoid using lambda ^^^
            for nne in ne.ready:
                if nne.energy>=50:
                    e = self.notSafeUnit.closer_than(15,nne)
                    a = self.quarryUnits.exclude_type(uId.PROBE)
                    ac = a.closer_than(30,nne)
                    a = a.further_than(50, nne)
                    if len(e)>len(ac)+5 and len(a)>len(e)+5:
                        if await self.can_cast(nne, AbilityId.EFFECT_MASSRECALL_NEXUS, a.random.position):
                            nne(AbilityId.EFFECT_MASSRECALL_NEXUS, a.random.position)
                    elif b.closer_than(8,nne):
                        if await self.can_cast(nne, AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, b.closest_to(nne)):
                            nne(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, b.closest_to(nne))
        if motherShip and not self.already_pending(uId.MOTHERSHIP):
            fb = self.quarryStructures(uId.FLEETBEACON).ready
            if fb.exists and n.idle.exists:
                if self.can_afford(uId.MOTHERSHIP):
                    n.idle.closest_to(self.start_location).train(uId.MOTHERSHIP)

    async def findBuildingLocationFixer(self, nexusHop=5,mineralHops=5,structureJumps=6):
        pl = self.quarryStructures(uId.PYLON).ready
        n = self.quarryStructures(uId.NEXUS)
        if pl.exists:
            if len(pl) > 1:
                pl.remove(pl.first)
            p = pl.random.position
            if n.exists:
                p=p.towards(n.closest_to(p),-nexusHop)
            m = self.avoidObstacle
            if m.exists:
                for i in range(mineralHops):
                    p = p.towards(m.closest_to(p), -1)
            for i in range(structureJumps):
                p = p.towards(self.quarryStructures.closest_to(p),-1)
            if self.quarryEnemyStructure.exists:
                e = self.quarryEnemyStructure.closest_to(self.start_location)
                if e.distance_to(p) < e.distance_to(self.rallyPointDefend):
                    self.rallyPointDefend = p.towards(self.pathingLocationCheck,4)
            return p
        else:
            return self.start_location

    async def findExpandLocation(self, mineralClusterSize=13,enemyDistance=25,nexusDistance=10,maxHops=12): # threshhold used as radius is 6.5 in docu for something else so 13 is cluster diameter
        n = self.quarryUnits(uId.NEXUS)
        m = self.mineral_field
        e = self.notSafeUnit | self.quarryEnemyStructure
        while m.exists:
            p = m.closest_to(self.start_location).position
            mm = m.closer_than(mineralClusterSize, p)
            if e.closer_than(enemyDistance, p):
                for mmm in mm:
                    m.remove(mmm)
            elif n.closer_than(9,p).exists:
                for mmm in mm:
                    m.remove(mmm)
            else:
                p = mm.center
                for i in range(maxHops):
                    p = p.towards(m.closest_to(p),-1)
                    if await self.can_place(uId.NEXUS, p):
                        return p
                for mmm in mm:
                    m.remove(mmm)
                #return p.towards(mm.closest_to(p),-2)
        return None

    async def gateWayLogic(self, num=1, supplyStop=125, mineralBuffer=150):
        g = self.quarryStructures(uId.GATEWAY)
        if len(g)<num and not self.already_pending(uId.GATEWAY) and self.minerals>mineralBuffer*(1+len(g)):
            pr = self.workerBuilder
            pl = self.quarryStructures(uId.PYLON)
            if self.can_afford(uId.GATEWAY) and pr.exists and pl.ready.exists:
                p = await self.findBuildingLocationFixer()
                p = await self.find_placement(uId.GATEWAY, near=p)
                if not p is None:
                    pr = pr.closest_to(p)
                    pr.build(uId.GATEWAY,p)
        if not self.trainingBlock:
            for gg in g.ready.idle:
                if self.supply_used < supplyStop and not self.trainingBlock:
                    st = len(self.quarryUnits(uId.STALKER))
                    z = len(self.quarryUnits(uId.ZEALOT))
                    if z-self.zealotPlus > st-self.stalkerPlus: # subtraction instead of addition because cross math is harder to visualize
                        if self.can_afford(uId.STALKER):
                            gg.train(uId.STALKER)
                    elif self.can_afford(uId.ZEALOT):
                        gg.train(uId.ZEALOT)

    async def starGateLogic(self, num=1, vespeneMulti=150, oNum=0, pNum=0, vNum=0, tNum=0, cNum=0):
        s = self.quarryStructures(uId.STARGATE)
        c = self.quarryStructures(uId.CYBERNETICSCORE)
        if num>len(s) and vespeneMulti*(len(s)+1) <= self.vespene and not self.already_pending(uId.STARGATE):
            pr = self.workerBuilder
            pl = self.quarryStructures(uId.PYLON)
            if self.can_afford(uId.STARGATE) and pr.exists and pl.ready.exists and c.ready.exists:
                p = await self.findBuildingLocationFixer()
                p = await self.find_placement(uId.STARGATE, near=p)
                if not p is None:
                    pr = pr.closest_to(p)
                    pr.build(uId.STARGATE, p)
        if not (self.starGateBlock or self.trainingBlock):
            o = self.quarryUnits(uId.ORACLE)
            p = self.quarryUnits(uId.PHOENIX)
            v = self.quarryUnits(uId.VOIDRAY)
            t = self.quarryUnits(uId.TEMPEST)
            c = self.quarryUnits(uId.CARRIER)
            e = self.notSafeUnit.closer_than(30,self.start_location)
            for ss in s.ready.idle:
                if not e.exists and len(o)==0 and not self.already_pending(uId.ORACLE) and oNum>0 and self.can_afford(uId.ORACLE):
                    ss.train(uId.ORACLE)
                elif len(t) < tNum and self.can_afford(uId.TEMPEST):
                    ss.train(uId.TEMPEST)
                elif len(c) < cNum and self.can_afford(uId.CARRIER):
                    ss.train(uId.CARRIER)
                #elif len(o) + self.already_pending(uId.ORACLE) < oNum and self.can_afford(uId.ORACLE):
                elif len(o) < oNum and self.can_afford(uId.ORACLE) and not self.already_pending(uId.ORACLE): # last part disables mass oracle
                    ss.train(uId.ORACLE)
                elif len(v)-vNum <= len(p)-pNum and self.can_afford(uId.VOIDRAY):
                    ss.train(uId.VOIDRAY)
                elif len(p)-pNum <= len(v)-vNum and self.can_afford(uId.PHOENIX):
                    ss.train(uId.PHOENIX)

    async def cCoreLogic(self):
        c = self.quarryStructures(uId.CYBERNETICSCORE)
        if not c.exists and not self.already_pending(uId.CYBERNETICSCORE):
            pr = self.workerNotBuilding
            pl = self.quarryStructures(uId.PYLON)
            if pr.exists and pl.exists:
                p = await self.findBuildingLocationFixer()
                p = await self.find_placement(uId.CYBERNETICSCORE, near=p)
                if not p is None:
                    pr = pr.closest_to(p)
                    pr.build(uId.CYBERNETICSCORE, p)
        for cc in c.ready.idle:
            if await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1)
            elif await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1)
            elif await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2)
            elif await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2)
            elif await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3)
            elif await self.can_cast(cc, AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3) and self.can_afford(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3):
                cc(AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3)

    async def fleetBeaconLogic(self, costThreshHold=300):
        f = self.quarryStructures(uId.FLEETBEACON)
        if self.vespene>costThreshHold and self.minerals>costThreshHold and not f.exists and not self.already_pending(uId.FLEETBEACON):
            sg = self.quarryStructures(uId.STARGATE).ready
            pr = self.workerBuilder
            pl = self.quarryStructures(uId.PYLON)
            if sg.exists and pr.exists and pl.exists:
                p = await self.findBuildingLocationFixer()
                p = await self.find_placement(uId.FLEETBEACON, near=p)
                if not p is None:
                    pr = pr.closest_to(p)
                    pr.build(uId.FLEETBEACON, p)
        for ff in f.ready.idle:
            if await self.can_cast(ff, AbilityId.RESEARCH_PHOENIXANIONPULSECRYSTALS) and self.can_afford(AbilityId.RESEARCH_PHOENIXANIONPULSECRYSTALS):
                ff(AbilityId.RESEARCH_PHOENIXANIONPULSECRYSTALS)
            elif await self.can_cast(ff, AbilityId.FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE) and self.can_afford(AbilityId.FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE):
                ff(AbilityId.FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE)
            # There is an upgrade for tempests to do extra damage to buildings. Buildings isn't armies and the upgrade costs money. Intentionally left out. Spending resources on something that does not fight back is a terrible idea.

    async def forgeLogic(self, mineralSurplus=350, researchGroundUnitTheshhold=10, twilightCouncil=True):
        e = self.quarryStructures(uId.FORGE)
        g = self.quarryUnits.exclude_type(uId.PROBE).not_flying
        for ee in e.ready.idle:
            if await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1):
                ee(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1)
            elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2):
                ee(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2)
            elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3):
                ee(AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3)
            elif researchGroundUnitTheshhold <= len(g):
                if await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1)
                elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2)
                elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3)
                elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1)
                elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2)
                elif await self.can_cast(ee, AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3) and self.can_afford(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3):
                    ee(AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3)
        if self.minerals > mineralSurplus and not e.exists and not self.already_pending(uId.FORGE):
            pr = self.workerBuilder
            pl = self.quarryStructures(uId.PYLON).ready
            if pr.exists and pl.exists:
                p = await self.findBuildingLocationFixer()
                p = await self.find_placement(uId.FORGE, near=p)
                if not p is None:
                    pr = pr.closest_to(p)
                    pr.build(uId.FORGE, p)
                #await self.build(uId.FORGE, near=pl.random)
        if twilightCouncil:
            tw = self.quarryStructures(uId.TWILIGHTCOUNCIL)
            if e.ready.exists:
                if self.minerals > mineralSurplus and self.vespene > mineralSurplus:
                    if not tw.exists:
                        if not self.already_pending(uId.TWILIGHTCOUNCIL):
                            pr = self.workerBuilder
                            pl = self.quarryStructures(uId.PYLON).ready
                            if pr.exists and pl.exists:
                                p = await self.findBuildingLocationFixer()
                                p = await self.find_placement(uId.TWILIGHTCOUNCIL, near=p)
                                if not p is None:
                                    pr = pr.closest_to(p)
                                    pr.build(uId.TWILIGHTCOUNCIL, p)
                                    #await self.build(uId.TWILIGHTCOUNCIL, near=pl.random)
                    else:
                        s = self.quarryUnits(uId.STALKER)
                        z = self.quarryUnits(uId.ZEALOT)
                        for twtw in tw.ready.idle:
                            if await self.can_cast(twtw, AbilityId.RESEARCH_BLINK) and self.can_afford(AbilityId.RESEARCH_BLINK) and len(s)>researchGroundUnitTheshhold/2:
                                twtw(AbilityId.RESEARCH_BLINK)
                            elif await self.can_cast(twtw, AbilityId.RESEARCH_CHARGE) and self.can_afford(AbilityId.RESEARCH_CHARGE) and len(z)>researchGroundUnitTheshhold/2:
                                twtw(AbilityId.RESEARCH_CHARGE)

    async def powerUnpowered(self):
        pr = self.workerBuilder
        u = self.quarryStructures.exclude_type(uId.PYLON).exclude_type(uId.NEXUS).exclude_type(uId.ASSIMILATOR).exclude_type(uId.ASSIMILATORRICH).ready.filter(lambda s: not s.is_powered)
        if pr.exists and u.exists:
            if not self.already_pending(uId.PYLON):
                await self.build(uId.PYLON, near=u.random.position)

    async def lateGameCheck(self):
        t = self.quarryUnits(uId.TEMPEST)
        if t.exists:
            self.midDone = True
        elif self.minerals>1000 and self.vespene>400:
            self.midDone = True
    # army macro
    async def proximityDefend(self, safeDistance=15, hopDistance=15):
        # there is a known weakness where middle bases are not defended. This is a sacrifice for performance.
        e = self.notSafeUnit
        es = e.filter(lambda ee: ee.has_buff(BuffId.ORACLESTASISTRAPTARGET))
        if es.exists:
            a = self.quarryUnits.exclude_type(uId.PROBE)
            for aa in a:
                aa.attack(es.closest_to(aa).position)
        elif e.exists:
            ee = e.closest_to(self.start_location)
            d = ee.distance_to(self.quarryStructures.closest_to(ee))
            a = self.quarryUnits.exclude_type(uId.PROBE)
            if d<safeDistance:
                if a.exists:
                    p = a.center.towards(ee, hopDistance)
                    for aa in a:
                        aa.attack(p) # look up attack move in rts games. Attacking ground on purpose
                if len(e)>2:
                    self.rallyPointDefend = ee.position
                    self.hasBeenAttacked = True

    async def rally(self, hopDistance=20):
        # oracle excluded from army for two reasons
        # It can be an outlier when calculating army center because of scouting
        # It is too fragile to be frontline late game so it needs to be moved to army center instead of army center towards enemy
        a = self.quarryUnits.exclude_type(uId.PROBE).exclude_type(uId.ORACLE)
        e = self.notSafeUnit | self.quarryEnemyStructure
        if not self.mineral_field.exists:
            print("untested check if minerals exist")
            a = self.quarryUnits
        if a.exists:
            if self.supply_used < 190:
                #a = a.exclude_type(uId.ORACLE) # moved
                p = self.rallyPointDefend
                if a.exists:
                    p = p.towards(a.center, hopDistance)
                for aa in a.idle | self.quarryUnits(uId.MOTHERSHIP): # done weird to stop a behavior of mothership being left behind on a step back which is fifne for oher units but this one is too expensive
                    aa.attack(p)
            elif e.exists:
                p = e.closest_to(self.rallyPointDefend).position
                ac = a.center
                for aa in a:#.idle:
                    aa.attack(ac.towards(p,20))
                for o in self.quarryUnits(uId.ORACLE).filter(lambda oo: oo.energy>50):#.idle:
                    """
                    .idle removed because oracle code exists in at least 3 different places.
                    Oracle micro is run every game step.
                    This should run every 20 steps
                    # micro > stay with army when attacking > do other things
                    # it's messy but removing idle kind of works
                    """
                    p = None
                    if self.quarryUnits(uId.MOTHERSHIP).exists:
                        p = self.quarryUnits(uId.MOTHERSHIP).first.position
                    if p is not None:
                        o.move(p)
            elif self.mineral_field.exists:
                m = self.mineral_field | self.vespene_geyser # every logically place base requires minerals or a geyser. Using these as random inputs will eventually find all bases.
                for aa in a.idle:
                    aa.attack(m.random.position)
            else: # untested and will show up in less than .01% of games. Requires map to be completely mined out with no known enemy base locations.
                for aa in a.idle:
                    aa.attack(self.enemy_start_locations[0])

    async def scout(self, centerHop=25,ranMineralHop=15):
        o = self.quarryUnits(uId.ORACLE)
        e = self.quarryEnemy
        if not e.exists:
            if self.avoidObstacle.exists:
                for oo in o.idle:
                    oo.move(self.avoidObstacle.random.position)
        elif not e.visible.exists:
        #else:
            m = self.avoidObstacle
            for oo in o.idle:
                p = self.rallyPointDefend.towards(self.game_info.map_center, centerHop)
                if m.exists:
                    p = p.towards(m.random.position,ranMineralHop)
                oo.move(p)

    async def handleTrappedUnits(self,tooManyIdle=4):
        a = self.quarryUnits.exclude_type(uId.PROBE).not_flying
        if a.exists:
            ac = a.center
            a = a.filter(lambda aa: aa.distance_to(ac) > 10)
        #pr = self.quarryUnits(uId.PROBE)
        pr = self.workerNotBuilding.idle
        n = self.quarryStructures(uId.NEXUS).ready.filter(lambda nn: nn.energy > 50)
        m = self.quarryUnits(uId.MOTHERSHIP)#.filter(lambda mm: mm.energy > 50)
        if a.exists:
            aa = a.random
            path = await self.client.query_pathing(aa, self.pathingLocationCheck)
            if path is None:
                if m.exists:
                    m = m[0]
                    print("M warp a")
                    if await self.can_cast(m, AbilityId.EFFECT_MASSRECALL_STRATEGICRECALL, aa.position):
                        print("M true warp a")
                        m(AbilityId.EFFECT_MASSRECALL_STRATEGICRECALL, aa.position)
                elif n.exists:
                    print("N warp a")
                    nn = n.closest_to(self.pathingLocationCheck)
                    if await self.can_cast(nn, AbilityId.EFFECT_MASSRECALL_NEXUS,aa.position):
                        print("N true warp a")
                        nn(AbilityId.EFFECT_MASSRECALL_NEXUS, aa.position)
        if pr.exists and self.mineral_field.exists:
            if n.exists:
                min = self.mineral_field
                #pr = pr.filter(lambda prpr: self.mineral_field.closest_to(prpr).distance_to(prpr)>mineralDistance)
                if len(pr) >= tooManyIdle:
                    n2 = n
                    for nn in n2:
                        if await self.client.query_pathing(nn.position,self.pathingLocationCheck) is None:
                            n.remove(nn)
                            print("remove a nexus")
                else:
                    n = n.filter(lambda nn: nn.ideal_harvesters>nn.assigned_harvesters)
                if pr.exists and n.exists:
                    prpr = pr.random
                    path = await self.client.query_pathing(prpr,self.pathingLocationCheck)
                    if path is None:
                        nn = n.random
                        print("N warp pr")
                        if await self.can_cast(nn, AbilityId.EFFECT_MASSRECALL_NEXUS,prpr.position):
                            print("N true warp pr")
                            nn(AbilityId.EFFECT_MASSRECALL_NEXUS, prpr.position)

    async def armyWaitGroup(self, armyRatio=.6, groupRadius=8, excludeGround=False, exclude=None):
        if exclude is None:
            exclude = []
        a = self.quarryUnits.exclude_type(uId.PROBE)
        for ex in exclude:
            a = a.exclude_type(ex)
        if excludeGround:
            a = a.flying
        if a.exists:
            aa = a.furthest_to(self.start_location)
            e = self.enemy_structures
            if e.exists:
                aa = a.closest_to(e.closest_to(self.start_location))
            front = a.closer_than(groupRadius, aa)
            if float(front.amount) / a.amount < armyRatio:
                for f in front:
                    f.move(a.center)

    async def oracleEarlyScout(self, safeDistance=10):
        if not self.quarryEnemyStructure.exists:
            for oo in self.quarryUnits(uId.ORACLE):
                oo.move(self.enemy_start_locations[0])

    async def fixWorkers(self, mineralDistance=8, gasDistance=8):
        pr = self.quarryUnits(uId.PROBE)
        n = self.quarryStructures(uId.NEXUS).ready
        if pr.exists and n.exists:
            gas = self.quarryStructures(uId.ASSIMILATOR) | self.quarryStructures(uId.ASSIMILATORRICH)
            ng = gas.not_ready
            gas = gas.ready
            target = []
            idle = []
            for ngng in ng:
                prpr = pr.closer_than(2,ngng)
                if len(prpr) == 1:
                    prpr = prpr.closest_to(ngng)
                    #if checkOrder(prpr, AbilityId.WORKERSTOPIDLEABILITYVESPENE_GATHER):
                        #idle.append(prpr)
                        #if self.mineral_field.exists:
                            #prpr.gather(self.mineral_field.closest_to(prpr))
                    idle.append(prpr)
            for prpr in pr.idle:
                if prpr.is_carrying_resource:
                    prpr.return_resource()
                else:
                    idle.append(prpr)
            for gg in gas:
                x = gg.assigned_harvesters - gg.ideal_harvesters
                if x > 0:
                    prg = pr.closer_than(gasDistance,gg).filter(lambda prpr: checkOrder(prpr, AbilityId.HARVEST_GATHER))
                    if prg.exists:
                        idle.append(prg.first)
                elif x < 0:
                    target.append(gg)
            for nn in n:
                x = nn.assigned_harvesters - nn.ideal_harvesters
                if x != 0:
                    m = self.mineral_field.closer_than(mineralDistance, nn)
                    if m.exists:
                        if x > 0:
                            prm = pr.closer_than(mineralDistance, nn)
                            for i in range(x):
                                if prm.exists:
                                    prpr = prm.first
                                    prm.remove(prpr)
                                    idle.append(prpr)
                        elif x < 0:
                            m = self.mineral_field.closer_than(mineralDistance,nn)
                            x = x * -1
                            for i in range(x):
                                if m.exists:
                                    mm = m.first
                                    m.remove(mm)
                                    target.append(mm)
            if len(idle)>0 and len(target)>0:
                if self.vespene > self.minerals:
                    target.reverse() # vespene gas buildings are process before minerals, so flipping the list gives minerals priority
                tt = Units(target,bot_object=self) # minerals are treated as units for some reason in api
                #while tt.first is Units: # unknown error causes a list within a list instead of a single list. This fixes it.
                ii = Units(idle,bot_object=self)
                while len(tt)>0 and len(ii)>0:
                    ttt = tt.first
                    iii = ii.closest_to(ttt)
                    # I think python does a short circuit instead of logical operator so the 2nd hald of or should usually be ignored
                    # it's just a back up.

                    if not await  self.client.query_pathing(iii.position, ttt.position.towards(iii.position, ttt.radius)) is None or not await self.client.query_pathing(iii.position, ttt.position.towards(iii.position, -ttt.radius)) is None:
                    #if not await self.client.query_pathing(iii.position, ttt.position) is None:
                        tt.remove(ttt)
                        ii.remove(iii)
                        iii.gather(ttt)
                    elif await self.client.query_pathing(iii.position, self.pathingLocationCheck) is None:
                        print("worker pathing block")
                        ii.remove(iii)
                    elif await self.client.query_pathing(ttt.position, self.pathingLocationCheck) is None:
                        print("target pathing block")
                        tt.remove(ttt)
                    elif len(tt)>len(ii):
                        tt.remove(ttt)
                    else: # elif len(ii)>len(iii):
                        ii.remove(iii)
                iip = ii.idle
                if iip.exists:
                    p = iip.center
                    for iii in iip:
                        #iii.move(p)
                        iii.stop()

    async def adjustEnemy(self):
        zPlus = self.zealotPlus # instantiate variables with random filler to avoid of out scope
        sPlus = self.stalkerPlus # instantiate variables with random filler to avoid of out scope
        phPlus = self.phoenixPlus # instantiate variables with random filler to avoid of out scope
        vPlus = self.voidRayPlus # instantiate variables with random filler to avoid of out scope
        armyTotal=self.quarryEnemy
        if self.enemFaction == Race.Terran:
            zPlus = (armyTotal(uId.MARAUDER).amount*2) + (armyTotal(uId.BARRACKSTECHLAB).amount*2)
            sPlus = armyTotal(uId.REAPER).amount + ((armyTotal(uId.HELLION)|armyTotal(uId.HELLIONTANK)).amount*2) + (armyTotal(uId.GHOST).amount*4) + ((armyTotal(uId.VIKING)|armyTotal(uId.VIKINGFIGHTER)|armyTotal(uId.VIKINGASSAULT)).amount*2) + (armyTotal(uId.BARRACKSREACTOR).amount*2) + (armyTotal(uId.STARPORT).amount*2)
            phPlus = (armyTotal(uId.BANSHEE).amount*3) + ((armyTotal(uId.VIKING)|armyTotal(uId.VIKINGFIGHTER)|armyTotal(uId.VIKINGASSAULT)).amount*2) + (armyTotal(uId.STARPORT).amount*2)
            vPlus = (armyTotal(uId.MARAUDER).amount*2) + (armyTotal(uId.BATTLECRUISER).amount * 6) + (armyTotal(uId.THOR).amount * 2) + (armyTotal(uId.FACTORY).amount*2)
        elif self.enemFaction == Race.Zerg:
            zPlus = (armyTotal(uId.ZERGLING).amount /2)
            sPlus = (armyTotal(uId.MUTALISK).amount *2) + armyTotal(uId.ROACH).amount + armyTotal(uId.ROACHWARREN).amount + armyTotal(uId.SPIRE).amount
            phPlus = (armyTotal(uId.MUTALISK).amount * 2)
            vPlus = (armyTotal(uId.CORRUPTOR).amount * 2)
        elif self.enemFaction == Race.Protoss:
            zPlus = armyTotal(uId.IMMORTAL).amount*3
            sPlus = (armyTotal(uId.PHOENIX).amount * 2) + (armyTotal(uId.VOIDRAY).amount*3) + (armyTotal(uId.TEMPEST).amount * 3) + (armyTotal(uId.CARRIER).amount*3) + (armyTotal(uId.COLOSSUS).amount*3) + (armyTotal(uId.SENTRY).amount*2) + (armyTotal(uId.STARGATE).amount * 3) + (armyTotal(uId.HIGHTEMPLAR).amount * 3)
            phPlus = (armyTotal(uId.PHOENIX).amount * 2) + (armyTotal(uId.VOIDRAY).amount * 3) + (armyTotal(uId.STARGATE).amount * 3)
            vPlus = (armyTotal(uId.CARRIER).amount * 6) + (armyTotal(uId.STALKER).amount*2)
        else:
            if self.quarryEnemy.exists:
                self.enemFaction = self.quarryEnemy.first.race
        if self.minerals > 1000 and self.vespene < 500 and self.vespene>0:
            zPlus += self.minerals / (self.vespene*2)
        if zPlus/2 > self.zealotPlus:
            self.zealotPlus=zPlus/2
        if sPlus/2 > self.stalkerPlus:
            self.stalkerPlus=sPlus/2
        if phPlus/2 > self.phoenixPlus:
            self.phoenixPlus=phPlus/2
        if vPlus/2 > self.voidRayPlus:
            self.voidRayPlus=vPlus/3 # 3 instead of 2 because of supply used
    # unit micro
    async def probeMicro(self, checkDistance=8):
        pr = self.workerBuilder#self.quarryUnits(uId.PROBE) old code changed to only have units that aren't returning resources or building
        e = self.quarryEnemyUnit
        if pr.exists and e.exists:
            for prpr in pr:
                if prpr.shield<=2:
                    if e.closer_than(checkDistance, prpr).exists:
                        prpr.move(prpr.position.towards(e.closest_to(prpr),-5))
                elif prpr.distance_to(self.quarryStructures.closest_to(prpr))<checkDistance:
                    eg = e.not_flying.closer_than(checkDistance,prpr)
                    if prpr.weapon_cooldown < .1:
                        if eg.exists and eg.amount > countHasAbility(pr, AbilityId.ATTACK):
                            prpr.attack(eg.closest_to(prpr))
                    elif self.mineral_field.exists:
                        if eg.exists:
                            prpr.gather(self.mineral_field.closest_to(eg.closest_to(prpr)))
                        else:
                            prpr.gather(self.mineral_field.closest_to(prpr))
                elif checkOrder(prpr, AbilityId.ATTACK):
                    prpr.move(self.quarryStructures.closest_to(prpr).position)
                #else:
                #    prpr.move(self.quarryStructures.closest_to(prpr).position)

    # skipping zealotMicro because melee macro is worse than ranged micro charge is self cast.

    async def stalkerMicro(self):
        e = self.quarryEnemyUnit
        st = self.quarryUnits(uId.STALKER)
        f = self.quarryUnits.flying
        p = self.quarryEnemyUnit(uId.SIEGETANKSIEGED) | self.quarryEnemyUnit(uId.BATTLECRUISER) | self.quarryEnemyStructure(uId.MISSILETURRET) | self.quarryEnemyUnit(uId.GHOST) | self.quarryEnemyUnit(uId.VIKING) | self.quarryEnemyUnit(uId.WIDOWMINE) | self.quarryEnemyUnit(uId.WIDOWMINEBURROWED) | self.quarryEnemyUnit(uId.MEDIVAC)
        p = p | self.quarryEnemyUnit(uId.CORRUPTOR) | self.quarryEnemyUnit(uId.VIPER) | self.quarryEnemyUnit(uId.INFESTOR)
        p = p | self.quarryEnemyUnit(uId.MOTHERSHIP) | self.quarryEnemyUnit(uId.TEMPEST) | self.quarryEnemyUnit(uId.CARRIER) | self.quarryEnemyUnit(uId.TEMPEST) | self.quarryEnemyUnit(uId.HIGHTEMPLAR)
        for stst in st:
            if stst.weapon_ready:
                if await self.can_cast(stst,AbilityId.EFFECT_BLINK_STALKER,stst.position) and p.closer_than(6+8,stst).exists:
                    if p.closest_to(stst).distance_to(stst)>6:
                        stst(AbilityId.EFFECT_BLINK_STALKER, stst.position.towards(p.closest_to(stst),8))
                    else:
                        stst.attack(p.closest_to(stst))
                else:
                    e=self.quarryUnits.enemy.closer_than(6,stst.position)
                    if e.exists:
                        if f.exists:
                            if e.filter(lambda ee: ee.can_attack_flying).exists:
                                e = e.filter(lambda ee: ee.can_attack_flying)
                        if e.filter(lambda ee: ee.is_armored).exists:
                            e = e.filter(lambda ee: ee.is_armored)
                        stst.attack(e.closest_to(stst))
            elif e.closer_than(6,stst).exists:
                if stst.shield < 10 and stst.health < 60 and await self.can_cast(stst,AbilityId.EFFECT_BLINK_STALKER,stst.position):
                    stst(AbilityId.EFFECT_BLINK_STALKER, stst.position.towards(e.closest_to(stst),-8))
                else:
                    stst.move(stst.position.towards(e.closest_to(stst).position,-1))

    async def phoenixMicro(self,attackBuffer=2):
        ef = self.notSafeUnit.flying # notSafeUnit used to prevent observer and overseer loss
        flyThreat = self.quarryEnemyAttackAir.flying
        eg = self.quarryEnemyUnit.filter(lambda ee: not (ee.is_flying or ee.is_structure or ee.is_massive))
        tower = self.quarryEnemyAttackAir.structure
        for ph in self.quarryUnits(uId.PHOENIX):
            efx = 0
            towerX = 0
            if flyThreat.exists:
                ft = flyThreat.closest_to(ph)
                efx = ft.distance_to(ph) - ft.air_range+attackBuffer
            if tower.exists:
                e = tower.closest_to(ph)
                towerX = e.distance_to(ph) - e.air_range+attackBuffer
            if ef.closer_than(ph.air_range+attackBuffer, ph).exists:
                # looks weird but phoenix can attack and move at same time
                # there is also two places where prioritization is needed
                ft = flyThreat.closer_than(ph.air_range, ph)
                if ft.exists: # prioritize attacking threats
                    ph.attack(ft.closest_to(ph))
                efef = ef.closer_than(ph.air_range+attackBuffer, ph) and flyThreat
                if efef.exists:
                    ef = efef
                efef = ef.closest_to(ph)
                ph.move(efef.position.towards(ph, ph.air_range - .2))
            elif efx<0 and flyThreat.exists: # avoid losing to things that outrange phoenix
                ph.attack(flyThreat.closest_to(ph))
            elif towerX<0 and tower.exists:
                t = tower.closest_to(ph)
                ph.move(t.position.towards(ph,t.air_range+attackBuffer+2))# 2 used instead of 1 because of radius
            elif eg.closer_than(5,ph).exists:
                egeg = eg.closer_than(5,ph)
                egegeg = egeg.filter(lambda eegg: eegg.can_attack_air)
                if egegeg.exists:
                    egeg = egegeg
                egeg = egeg.closest_to(ph)
                if len(self.quarryUnits.closer_than(ph.air_range+attackBuffer, ph).filter(lambda aa: aa.can_attack_air)) > 1:
                    if await self.can_cast(ph, AbilityId.GRAVITONBEAM_GRAVITONBEAM, egeg):
                        ph(AbilityId.GRAVITONBEAM_GRAVITONBEAM, egeg)

    async def oracleMicro(self,revelationDistance=16,revelationBuffer=3,attackBuffer=4,evadeBuffer=8):
        # 4 shows up a lot. It is from the wiki. oracle doesn't have a base attack while ability isn't in use. 4 is its range. Its range can't be referenced through normal ways.
        # oracle has more code in army macro commands and scouting
        o = self.quarryUnits(uId.ORACLE)
        if o.exists:
            e = self.quarryEnemy
            sneak = self.notSafeUnit.filter(lambda ee: ee.is_cloaked)
            # burrowed units unitTypeIds are added to manually sneak because is_borrowed doesn't work.
                # only included things that are worth revelation energy
                    #zergling burrow to block expansions is a common dumb bot strat so zergling is a worth the revelation energy
                # Burrowed units all have different UnitIds than non-burrowed units. I speculate the "is_burrowed" unit attribute is an artifact that was going to be implemented but the devs relized seperate unit Id worked better. I don't actually know.
                    # UnitId is set by the api maker. UnitId is set by a script and the script gets UnitId from the game files? Blizzard sets UnitId.
            sneak = sneak | e(uId.WIDOWMINEBURROWED) | e(uId.LURKERMPBURROWED) | e(uId.ZERGLINGBURROWED) | e(uId.ROACHBURROWED) | e(uId.INFESTORBURROWED) | e(uId.SWARMHOSTBURROWEDMP) | e(uId.DRONEBURROWED) | e(uId.BANELINGBURROWED)
            sneak = sneak.filter(lambda s: not s.has_buff(BuffId.ORACLEREVELATION))
            eg = e.not_flying
            for oo in o:
                egc = eg.closer_than(4+evadeBuffer,oo)
                #print("oracle debug")
                #print(self.time)
                a = self.quarryUnits.closer_than(4 + evadeBuffer, oo)
                threat = self.quarryEnemyAttackAir.closer_than(4 + evadeBuffer, oo)
                towerX = 1
                sneakX = revelationDistance+1
                # pre turret math
                if threat.structure.ready.exists:
                    ee = threat.structure.ready.closest_to(oo)
                    towerX = ee.distance_to(oo) - (ee.air_range+2)
                # pre revelation math
                if sneak.exists:
                    b = sneak.closest_to(oo).distance_to(oo)
                    if b < sneakX:
                        sneakX = b
                # if turret too close
                #print(towerX)
                #print(sneakX)
                # if need cast revelation
                if sneakX <= revelationDistance and oo.energy > 25:
                    oo(AbilityId.ORACLEREVELATION_ORACLEREVELATION, sneak.closest_to(oo).position.towards(oo, revelationBuffer))
                # if need retreat too low ;-;
                elif sneak.exists and oo.energy > 30:
                    oo.move(sneak.closest_to(oo).position.towards(oo,revelationDistance))
                elif towerX < 0:
                    #print("tower micro")
                    if threat.structure.exists:
                        t = threat.structure.closest_to(oo)
                        oo.move(t.position.towards(oo,t.air_range+evadeBuffer))
                elif oo.health + oo.shield < oo.shield_max and threat.exists:
                    #print("health low micro")
                    oo.move(oo.position.towards(threat.closest_to(oo),-5))
                # if has oracle weapon on
                elif oo.has_buff(BuffId.ORACLEWEAPON):
                    #print("oracle weapon micro")
                    #egc = eg.closer_than(4 + attackBuffer, oo)
                    # target prio
                    if egc.not_structure.exists:
                        egc = egc.not_structure
                    el = egc.filter(lambda ee: ee.is_light)
                    if el.exists:
                        egc = el
                    if (egc and threat).exists:
                        egc = egc and threat
                    if egc.exists and len(a) + 1 >= len(threat):
                        oo.attack(egc.closest_to(oo))
                    else:
                        oo(AbilityId.BEHAVIOR_PULSARBEAMOFF)
                        if threat.exists:
                            oo.move(oo.position.towards(threat.closest_to(oo), -10))
                # statis trap
                elif oo.energy == 200 or (oo.energy > 151 and not e.closer_than(15,oo).exists and not self.structures(uId.ORACLESTASISTRAP).closer_than(15, oo).exists):
                    #print("statis trap")
                    p = oo.position
                    st = self.structures(uId.ORACLESTASISTRAP).closer_than(4+evadeBuffer,oo)
                    if st.exists:
                        p = p.towards(st.center,-(evadeBuffer+attackBuffer))
                    p = await self.find_placement(uId.ORACLESTASISTRAP, near=p)
                    oo(AbilityId.BUILD_STASISTRAP, p)
                # check if need to turn weapon on
                elif oo.energy > 35 and egc.not_structure.exists and not oo.has_buff(BuffId.ORACLEWEAPON):
                    #print("check if need to turn on weapon or retreatt")
                    # winnable?
                    if len(a) + 1 >= len(threat):
                        if eg.not_structure.closer_than(4,oo).exists:
                            # beam on
                            oo(AbilityId.BEHAVIOR_PULSARBEAMON)
                        else:
                            # move to turn on beam
                            oo.move(eg.closest_to(oo).position)
                    elif threat.exists:
                        th = threat.closest_to(oo)
                        distance = 1+ revelationDistance - revelationBuffer
                        distance2 = th.air_range
                        if distance<distance2:
                            distance=distance2
                        if th.distance_to(oo)>distance:
                            oo.move(th.position.towards(oo,distance))
                # idle avoid getting shot at
                # python is short circuit operator for logic so this works
                elif threat.exists and threat.closest_to(oo).distance_to(oo)<threat.closest_to(oo).air_range+evadeBuffer:
                    #print("idle threat dodge")
                    oo.move(threat.closest_to(oo).position.towards(threat.closest_to(oo).position,15))# I don't think anything outranges 15
                # # no valid cast or attack
                #elif e.closer_than(4+evadeBuffer,oo).not_structure.exists: #rework
                # leave if enemy threat exists
                #elif self.quarryEnemyAttackAir.closer_than(4+evadeBuffer+evadeBuffer,oo).exists:
                    #print("enemy close default micro")
                #    oo.move(oo.position.towards(e.closest_to(oo),-10))
                # recharge
                elif oo.is_idle and oo.energy < 80:
                    #print("recharge")
                    n = self.quarryStructures(uId.NEXUS)
                    nn = n.filter(lambda ne: ne.energy>oo.energy)
                    if nn.exists:
                        n = nn
                    if n.exists:
                        oo.move(n.random.position)
                        if n.closer_than(11,oo).ready.exists:
                            if n.closest_to(oo).energy > 50:
                                n.closest_to(oo)(AbilityId.ENERGYRECHARGE_ENERGYRECHARGE,oo)
                # manually invoke scouting if no known enemies(includes structure)
                elif oo.is_idle and not self.quarryEnemy.exists:
                    #print("force scout")
                    await self.oracleEarlyScout()
                elif oo.is_idle and self.supply_used<120:
                    #print("idle")
                    #p = self.quarryUnits.center
                    p = self.rallyPointDefend
                    p = p.towards(self.quarryEnemy.random,evadeBuffer+evadeBuffer+attackBuffer)
                    oo.move(p)

    async def voidRayMicro(self, rangeBuffer=.75):
        v = self.quarryUnits(uId.VOIDRAY)
        for vv in v:
            ar = vv.air_range
            if ar==0:
                ar=6 # this for a random voidray bug where unit.weapon[0] returns index out of bounds because no weapon and air range is based off can_attack_air and can_attack_air is based off of unit.weapon in the api under unit
            e = self.quarryEnemyUnit.closer_than(ar+rangeBuffer, vv)
            if e.exists:
                ee = e.filter(lambda el: el.can_attack_air)
                if ee.exists:
                    e = ee
                ee = e.filter(lambda el: el.is_armored)
                if ee.exists:
                    e = ee
                    if not vv.has_buff(BuffId.VOIDRAYSWARMDAMAGEBOOST):
                        if await self.can_cast(vv, AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT):
                            vv(AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT)
                vv.attack(e.closest_to(vv))
            elif vv.has_buff(BuffId.VOIDRAYSWARMDAMAGEBOOST):
                if await self.can_cast(vv, AbilityId.CANCEL_VOIDRAYPRISMATICALIGNMENT):
                    vv(AbilityId.CANCEL_VOIDRAYPRISMATICALIGNMENT)

    async def tempestMicro(self):
        t = self.quarryUnits(uId.TEMPEST)
        for tt in t:
            e = self.quarryEnemyUnit.closer_than(tt.ground_range, tt)
            if e.exists:
                if tt.weapon_cooldown>0:
                    tt.move(tt.position.towards(e.closest_to(tt),-.5))
                else:
                    ee = e.closest_to(tt)
                    tt.attack(ee)

    async def motherShipMicro(self, slowCount=4,stealthCount=6,stealthDistance=10):
        m = self.quarryUnits(uId.MOTHERSHIP)
        if m.exists:
            m=m[0]
            #print(await self.client.query_available_abilities(m))
            e = self.quarryEnemyAttackAir
            if e.closer_than(6,m).exists: # 7 is range from the wiki
                m.move(m.position.towards(e.closest_to(m),-1))
            elif e.exists:
                ee = e.closest_to(m)
                if ee.air_range > ee.distance_to(m):
                    m.move(m.position.towards(ee,-2))
            if len(e.closer_than(9,m))>=slowCount and await self.can_cast(m, AbilityId.EFFECT_TIMEWARP,m.position):
                m(AbilityId.EFFECT_TIMEWARP,e.closest_to(m).position)
            if len(e.closer_than(stealthDistance,m))>=stealthCount and await self.can_cast(m, AbilityId.MOTHERSHIPCLOAK_ORACLECLOAKFIELD):
                m(AbilityId.MOTHERSHIPCLOAK_ORACLECLOAKFIELD)

# Static Helpers
def checkOrder(unit, ability):
    for o in unit.orders:
        if o.ability.id==ability:
            return True
    return False

def checkMultiOrder(unit, abilityList):
    for o in unit.orders:
        for a in abilityList:
            if o.ability.id == a:
                return True
    return False

def countHasAbility(units, ability):
    i = 0
    for u in units:
        if checkOrder(u,ability):
            i += 1
    return i