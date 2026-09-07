"""Compile production gameplay methods with an in-memory server and exercise travel UI.

Requires Python with lupa and a C++17 compiler. Use --compiler cl inside a Visual
Studio developer prompt on Windows. This does not replace a complete Core3 build.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[3]
CORE = ROOT / "MMOCoreORB"


def method(relative, signature):
    source = (CORE / relative).read_text(encoding="utf-8")
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("includeFile = function() end")
    lua.execute((CORE / "bin/scripts/managers/planet/planet_manager.lua").read_text())
    planets = []
    for name, value in lua.globals().items():
        if hasattr(value, "items") and value["planetTravelPoints"] is not None:
            points = value["planetTravelPoints"]
            if len(points):
                planets.append((name, [points[i] for i in range(1, len(points) + 1)]))
    planets.sort()
    assert len(planets) == 10, f"Unexpected planet fixture count: {len(planets)}"

    cpp = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#include "server/zone/managers/credit/CreditScale.h"
#include "server/zone/objects/creature/MovementScale.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"
using uint32 = uint32_t;
using uint64 = uint64_t;
struct String : std::string {
    using std::string::string;
    String(const std::string& text) : std::string(text) {}
    String toString() const { return *this; }
    String replaceAll(const String& from, const String& to) const {
        String out = *this;
        size_t pos = 0;
        while ((pos = out.find(from, pos)) != npos) { out.replace(pos, from.size(), to); pos += to.size(); }
        return out;
    }
    template<class T> static String valueOf(T value) { return std::to_string(value); }
};
using UnicodeString = String;
struct Integer { static int valueOf(const String& value) { return std::stoi(value); } };
template<class T> struct Reference {
    T ptr = nullptr;
    Reference(T value = nullptr) : ptr(value) {}
    T get() const { return ptr; }
    T operator->() const { return ptr; }
    operator T() const { return ptr; }
};
template<class T> using ManagedReference = Reference<T>;
template<class T> struct Vector : std::vector<T> {
    void add(const T& value) { this->push_back(value); }
    T& get(int index) { return this->at(index); }
    const T& get(int index) const { return this->at(index); }
    int size() const { return static_cast<int>(std::vector<T>::size()); }
};
template<class K, class V> struct VectorMap : std::map<K, V> {
    struct Entry { K key; const K& getKey() const { return key; } };
    mutable Entry entry;
    int size() const { return static_cast<int>(std::map<K, V>::size()); }
    const Entry& elementAt(int index) const { auto it = this->begin(); std::advance(it, index); entry.key = it->first; return entry; }
    void setAllowOverwriteInsertPlan() {}
    void setNullValue(V) {}
    bool contains(const K& key) const { return this->find(key) != this->end(); }
    V& get(const K& key) { return (*this)[key]; }
    void put(const K& key, const V& value) { (*this)[key] = value; }
};
template<class T, class U> T cast(U* value) { return dynamic_cast<T>(value); }
uint32 STRING_HASHCODE(const char*) { return 1; }
class Zone;
class PlanetManagerImplementation;
using PlanetManager = PlanetManagerImplementation;
class ZoneServer;
class CreatureObjectImplementation;
using CreatureObject = CreatureObjectImplementation;
class SuiBox;
struct CityRegion {
    bool banned = false, client = true;
    int tax = 0;
    bool isBanned(uint64) const { return banned; }
    bool isClientRegion() const { return client; }
    int getTravelTax() const { return tax; }
};
struct SceneObject { virtual ~SceneObject() = default; };
struct PlayerObject {
    Vector<SuiBox*> boxes;
    void addSuiBox(SuiBox* box) { boxes.add(box); }
};
struct Skill;
using SkillList = Vector<Reference<Skill*>>;
struct Locker { explicit Locker(void*) {} };
namespace CreaturePosture { enum { UPRIGHT, PRONE }; }
namespace CreatureState { enum { COVER }; }
struct SharedObjectTemplate {
    bool player = true;
    bool isPlayerCreatureTemplate() const { return player; }
};
class CreatureObjectImplementation : public SceneObject {
public:
    bool cover = false, rifleSkill = false;
    SharedObjectTemplate creatureTemplate;
    Reference<SharedObjectTemplate*> templateObject{&creatureTemplate};
    int posture = CreaturePosture::UPRIGHT;
    std::map<String, int> mods;
    ZoneServer* server = nullptr;
    Zone* zone = nullptr;
    PlayerObject ghost;
    Reference<CityRegion*> city;
    Vector<String> purchases;
    SkillList skills;
    std::map<String, int> skillBoxMods;
    int modUpdates = 0;
    const SkillList* getSkillList() const { return &skills; }
    int getSkillModOfType(const String& name, int) { return skillBoxMods[name]; }
    void addSkillMod(int, const String& name, int value, bool) { skillBoxMods[name] += value; ++modUpdates; }
    std::ostream& info() { return std::cout; }
    float getSpeedModifier() const;
    float getAccelerationModifier() const;
    // Match the non-const IDL declaration to catch calls from const methods.
    bool isPlayerCreature();
    int getSkillMod(const String& name) const { auto it = mods.find(name); return it == mods.end() ? 0 : it->second; }
    bool hasState(int) const { return cover; }
    bool hasSkill(const String&) const { return rifleSkill; }
    ZoneServer* getZoneServer() { return server; }
    PlayerObject* getPlayerObject() { return &ghost; }
    Zone* getZone() { return zone; }
    Reference<CityRegion*> getCityRegion() { return city; }
    uint64 getObjectID() const { return 42; }
    void sendMessage(void*) {}
    void executeObjectControllerAction(uint32, uint64, const String& arguments) { purchases.add(arguments); }
};
struct Skill {
    VectorMap<String, int> skillModifiers;
    VectorMap<String, int>* getSkillModifiers() { return &skillModifiers; }
};
class SkillModManager {
public:
    enum { SKILLBOX = 0x103 };
    void verifySkillBoxSkillMods(CreatureObject*);
    bool compareMods(VectorMap<String, int>&, CreatureObject*, int) { return true; }
};
class SkillManager {
public:
    std::map<String, Skill> skills;
    Skill* getSkill(const String& name) { auto it = skills.find(name); return it == skills.end() ? nullptr : &it->second; }
    void warning(const String&) {}
    void applyMasterSkillBonuses();
};
struct PlanetTravelPoint {
    String planet, name;
    bool interplanetary = false, incoming = true;
    CreatureObject shuttle;
    bool shuttleAvailable = true;
    const String& getPointZone() const { return planet; }
    const String& getPointName() const { return name; }
    bool isInterplanetary() const { return interplanetary; }
    bool isIncomingAllowed() const { return incoming; }
    CreatureObject* getShuttle() { return shuttleAvailable ? &shuttle : nullptr; }
    bool canTravelTo(const PlanetTravelPoint* arrivalPoint) const;
    bool isPoint(const String& p, const String& n) const { return p == planet && n == name; }
};
struct Zone {
    String name;
    PlanetManager* manager = nullptr;
    ZoneServer* server = nullptr;
    PlanetManager* getPlanetManager() { return manager; }
    ZoneServer* getZoneServer() { return server; }
};
class ZoneServer {
public:
    Vector<Zone*> zones;
    Zone* getZone(int index) { return zones.get(index); }
    Zone* getZone(const String& name) { for (auto z : zones) if (z && z->name == name) return z; return nullptr; }
    int getZoneCount() const { return zones.size(); }
};
struct ZoneProcessServer { ZoneServer* server; ZoneServer* getZoneServer() { return server; } };
class PlanetManagerImplementation {
public:
    Zone* zone = nullptr;
    ZoneProcessServer* server = nullptr;
    Vector<PlanetTravelPoint*> points;
    VectorMap<String, VectorMap<String, int>> travelFares;
    int getTravelFare(const String&, const String&);
    bool isTravelToLocationPermitted(const String&, const String&, const String&);
    PlanetTravelPoint* getPlanetTravelPoint(const String& name) { for (auto p : points) if (p->name == name) return p; return nullptr; }
    int getPlanetTravelPointCount() { return points.size(); }
    PlanetTravelPoint* getPlanetTravelPointByIndex(int index) { return points.get(index); }
    bool isExistingPlanetTravelPoint(const String& name) { return getPlanetTravelPoint(name) != nullptr; }
    bool isIncomingTravelAllowed(const String& name) { auto p = getPlanetTravelPoint(name); return p && p->incoming; }
    bool isInterplanetaryTravelAllowed(const String& name) { auto p = getPlanetTravelPoint(name); return p && p->interplanetary; }
};
struct TravelTerminal : SceneObject {
    Zone* zone;
    PlanetTravelPoint* point;
    bool near = true;
    Zone* getZone() { return zone; }
    PlanetTravelPoint* getPlanetTravelPoint() { return point; }
    bool isInRange(CreatureObject*, float) const { return near; }
    uint64 getObjectID() const { return 100; }
};
struct SuiCallback {
    ZoneServer* server;
    explicit SuiCallback(ZoneServer* value) : server(value) {}
    virtual ~SuiCallback() = default;
    virtual void run(CreatureObject*, SuiBox*, uint32, Vector<UnicodeString>*) = 0;
};
class SuiBox {
public:
    SuiCallback* callback = nullptr;
    Reference<SceneObject*> usingObject;
    virtual ~SuiBox() = default;
    virtual bool isListBox() const { return false; }
    Reference<SceneObject*> getUsingObject() { return usingObject; }
};
class SuiListBox : public SuiBox {
public:
    Vector<String> labels;
    Vector<uint64> ids;
    SuiListBox(CreatureObject*, int) {}
    bool isListBox() const override { return true; }
    void setCallback(SuiCallback* cb) { callback = cb; }
    void setUsingObject(SceneObject* obj) { usingObject = obj; }
    void setForceCloseDistance(float) {}
    void setPromptTitle(const String&) {}
    void setPromptText(const String&) {}
    void setCancelButton(bool, const String&) {}
    void addMenuItem(const String& name, uint64 id = 0) { labels.add(name); ids.add(id); }
    int getMenuSize() const { return labels.size(); }
    uint64 getMenuObjectID(int i) const { return ids.get(i); }
    void* generateMessage() { return nullptr; }
};
'''
    for file, signature in [
        ("src/server/zone/managers/skill/SkillManager.cpp", "void SkillManager::applyMasterSkillBonuses()"),
        ("src/server/zone/managers/skill/SkillModManager.cpp", "void SkillModManager::verifySkillBoxSkillMods("),
        ("src/server/zone/objects/creature/CreatureObjectImplementation.cpp", "float CreatureObjectImplementation::getSpeedModifier() const"),
        ("src/server/zone/objects/creature/CreatureObjectImplementation.cpp", "float CreatureObjectImplementation::getAccelerationModifier() const"),
        ("src/server/zone/objects/creature/CreatureObjectImplementation.cpp", "bool CreatureObjectImplementation::isPlayerCreature()"),
        ("src/server/zone/managers/planet/PlanetManagerImplementation.cpp", "int PlanetManagerImplementation::getTravelFare("),
        ("src/server/zone/managers/planet/PlanetManagerImplementation.cpp", "bool PlanetManagerImplementation::isTravelToLocationPermitted("),
    ]:
        cpp += "\n" + method(file, signature) + "\n"
    can_travel = method("src/server/zone/managers/planet/PlanetTravelPoint.h", "bool canTravelTo(")
    can_travel = can_travel.replace("bool canTravelTo(", "bool PlanetTravelPoint::canTravelTo(")
    can_travel = can_travel.replace("pointZone", "planet").replace("interplanetaryTravelAllowed", "interplanetary")
    cpp += can_travel + "\n"
    callback = (CORE / "src/server/zone/objects/player/sui/callbacks/StarportTravelSuiCallback.h").read_text()
    cpp += "\n".join(line for line in callback.splitlines() if not line.startswith("#"))
    cpp += r'''
int main() {
    SkillManager skills;
    skills.skills["social_dancer_master"].skillModifiers.put("healing_dance_mind", 25);
    skills.skills["social_musician_master"].skillModifiers.put("healing_music_mind", 25);
    skills.skills["science_doctor_master"].skillModifiers.put("healing_wound_treatment", 20);
    skills.skills["science_doctor_master"].skillModifiers.put("healing_wound_speed", 10);
    skills.skills["science_doctor_master"].skillModifiers.put("healing_ability", 30);
    skills.skills["social_dancer_novice"].skillModifiers.put("healing_dance_mind", 5);
    skills.applyMasterSkillBonuses();
    assert(skills.skills["social_dancer_master"].skillModifiers.get("healing_dance_mind") == 50);
    assert(skills.skills["social_musician_master"].skillModifiers.get("healing_music_mind") == 50);
    assert(skills.skills["science_doctor_master"].skillModifiers.get("healing_wound_treatment") == 45);
    assert(skills.skills["science_doctor_master"].skillModifiers.get("healing_wound_speed") == 35);
    assert(skills.skills["science_doctor_master"].skillModifiers.get("healing_ability") == 30);
    assert(skills.skills["social_dancer_novice"].skillModifiers.get("healing_dance_mind") == 5);
    CreatureObject player, npc;
    player.skills.add(&skills.skills["science_doctor_master"]);
    player.skillBoxMods["healing_wound_treatment"] = 20;
    // Wound speed is deliberately absent to exercise migration from old saves.
    SkillModManager skillMods;
    skillMods.verifySkillBoxSkillMods(&player);
    assert(player.skillBoxMods["healing_wound_treatment"] == 45);
    assert(player.skillBoxMods["healing_wound_speed"] == 35);
    int modUpdates = player.modUpdates;
    skillMods.verifySkillBoxSkillMods(&player);
    assert(player.modUpdates == modUpdates);
    npc.creatureTemplate.player = false;
    assert(player.isPlayerCreature() && !npc.isPlayerCreature());
    assert(player.getSpeedModifier() == 2.f && npc.getSpeedModifier() == 1.f);
    assert(player.getAccelerationModifier() == 2.f && npc.getAccelerationModifier() == 1.f);
    CreatureObject uninitialized;
    uninitialized.templateObject = nullptr;
    assert(!uninitialized.isPlayerCreature());
    assert(uninitialized.getSpeedModifier() == 1.f);
    assert(uninitialized.getAccelerationModifier() == 1.f);
    const CreatureObject& constPlayer = player;
    assert(constPlayer.getSpeedModifier() == 2.f);
    assert(constPlayer.getAccelerationModifier() == 2.f);
    player.mods["private_speed_multiplier"] = 150;
    assert(player.getSpeedModifier() == 3.f);
    player.mods.clear();
    player.posture = CreaturePosture::PRONE;
    player.cover = true;
    assert(player.getSpeedModifier() == 0.f);
    player.rifleSkill = true;
    assert(player.getSpeedModifier() == 1.f);
    player.posture = CreaturePosture::UPRIGHT;
    player.cover = false;
    // The rider is scaled once, after the mount/vehicle's base speed and buffs.
    assert(7.f * player.getSpeedModifier() == 14.f);
    assert(21.9f * player.getSpeedModifier() == 43.8f);
    assert(12.f * 1.5f * player.getSpeedModifier() == 36.f);
    ZoneServer server;
    ZoneProcessServer process{&server};
    std::map<String, Zone> zones;
    std::map<String, PlanetManager> managers;
    player.server = &server;
'''
    for name, points in planets:
        name_literal = json.dumps(name)
        cpp += f'''{{ auto& zone = zones[{name_literal}]; zone.name = {name_literal};
auto& manager = managers[{name_literal}]; zone.manager = &manager; zone.server = &server;
manager.zone = &zone; manager.server = &process; server.zones.add(&zone);
'''
        for point in points:
            cpp += "{ auto p = new PlanetTravelPoint(); "
            cpp += f"p->planet = {name_literal}; p->name = {json.dumps(point['name'])}; "
            cpp += f"p->interplanetary = {int(point['interplanetaryTravelAllowed'])}; p->incoming = {int(point['incomingTravelAllowed'])}; "
            cpp += "manager.points.add(p); }\n"
        cpp += "}\n"
    cpp += r'''
    int routes = 0;
    for (auto& originPair : managers) {
        auto& manager = originPair.second;
        player.zone = manager.zone;
        for (auto origin : manager.points) {
            if (!origin->interplanetary || !origin->incoming) continue;
            TravelTerminal terminal;
            terminal.zone = manager.zone; terminal.point = origin;
            StarportTravelSuiCallback::showDestinations(&player, &terminal, origin);
            auto destinations = dynamic_cast<SuiListBox*>(player.ghost.boxes.back());
            int expected = 0;
            for (auto& destinationPair : managers) {
                for (auto point : destinationPair.second.points) {
                    bool allowed = point != origin && point->incoming && (point->planet == origin->planet || point->interplanetary);
                    assert(manager.isTravelToLocationPermitted(origin->name, point->planet, point->name) == (allowed || point == origin));
                    if (allowed) { ++expected; assert(origin->canTravelTo(point)); }
                }
            }
            assert(destinations->getMenuSize() == expected);
            for (int i = 0; i < expected; ++i) {
                Vector<UnicodeString> row; row.add(String::valueOf(i));
                destinations->callback->run(&player, destinations, 0, &row);
                auto ticket = dynamic_cast<SuiListBox*>(player.ghost.boxes.back());
                assert(ticket != destinations && ticket->getMenuSize() == 2);
                assert(ticket->labels.get(0).find(" credits") != String::npos);
                for (int trip = 0; trip < 2; ++trip) {
                    Vector<UnicodeString> choice; choice.add(String::valueOf(trip));
                    int previous = player.purchases.size();
                    ticket->callback->run(&player, ticket, 0, &choice);
                    assert(player.purchases.size() == previous + 1);
                    assert(player.purchases.back().find(trip == 0 ? " single" : " roundtrip") != String::npos);
                    ++routes;
                }
                int previous = player.purchases.size();
                ticket->callback->run(&player, ticket, 1, &row);
                assert(player.purchases.size() == previous);
            }
            int boxes = player.ghost.boxes.size();
            Vector<UnicodeString> bad; bad.add("-1");
            destinations->callback->run(&player, destinations, 0, &bad);
            bad.get(0) = "9999";
            destinations->callback->run(&player, destinations, 0, &bad);
            bad.get(0) = "0";
            terminal.near = false;
            destinations->callback->run(&player, destinations, 0, &bad);
            assert(player.ghost.boxes.size() == boxes);
        }
    }
    auto& fares = managers["corellia"];
    fares.travelFares.get("corellia").put("naboo", 500);
    assert(fares.getTravelFare("corellia", "naboo") == 500);
    assert(CreditScale::credits(fares.getTravelFare("corellia", "naboo")) == 5);
    assert(CreditScale::credits(fares.getTravelFare("corellia", "rori")) == 10);
    assert(fares.getTravelFare("corellia", "disabled_planet") == 0);
    std::cout << "Master bonuses, movement and " << routes << " one-way/round-trip menu selections passed.\n";
}
'''
    with tempfile.TemporaryDirectory(prefix="solo_gameplay_") as tmp:
        tmp = Path(tmp)
        source = tmp / "gameplay.cpp"
        source.write_text(cpp, encoding="utf-8")
        executable = tmp / "gameplay_test.exe"
        if Path(args.compiler).stem.lower() == "cl":
            command = [args.compiler, "/nologo", "/EHsc", "/std:c++17", "/I" + str(CORE / "src"), str(source), "/Fe:" + str(executable), "/Fo:" + str(tmp / "gameplay.obj")]
        else:
            command = [args.compiler, "-std=c++17", "-I", str(CORE / "src"), str(source), "-o", str(executable)]
        subprocess.run(command, check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
