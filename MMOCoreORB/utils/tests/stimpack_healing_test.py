"""Check stimpack Lua definitions and compile the production area-healing methods.

Requires Python, lupa and a C++17 compiler, as does gameplay_tuning_test.py.
This exercises selected production methods, not a complete Core3 server build.
"""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from lupa import LuaRuntime

from gameplay_tuning_test import CORE, method


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        STIMPACK = 1; RANGEDSTIMPACK = 2
        STIM_A = 1; STIM_B = 2; STIM_C = 3; STIM_D = 4; STIM_E = 5
        ObjectTemplates = {addTemplate = function(self, definition, path) end}
    ''')
    templates = []
    for directory in ("medicine", "component/chemistry"):
        for path in sorted((CORE / "bin/scripts/object/tangible" / directory).rglob("*.lua")):
            source = path.read_text(encoding="utf-8")
            if not re.search(r"templateType\s*=\s*(?:STIMPACK|RANGEDSTIMPACK)\s*,", source):
                continue
            name, parent = re.search(r"(\w+)\s*=\s*(\w+):new\s*\{", source).groups()
            lua.globals()[parent] = lua.eval("{new = function(self, value) return value end}")
            lua.execute(source)
            definition = lua.globals()[name]
            attributes = list(definition["attributes"].values())
            templates.append((str(path.relative_to(CORE)), attributes, definition["templateType"] == 2))

    assert len(templates) == 27, f"Unexpected stimpack fixture count: {len(templates)}"
    missing_mind = [name for name, attributes, _ in templates if 6 not in attributes]
    assert not missing_mind, "Stimpacks missing Mind healing: " + ", ".join(missing_mind)
    assert all(attributes == [0, 3, 6] for _, attributes, _ in templates)

    cpp = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
using byte = uint8_t;
using uint32 = uint32_t;
using String = std::string;
namespace CreatureAttribute { enum { HEALTH = 0, ACTION = 3, MIND = 6 }; }
template<class T> struct Vector : std::vector<T> {
    using std::vector<T>::vector;
    bool contains(T value) const { return std::find(this->begin(), this->end(), value) != this->end(); }
};
template<class T, class U> T cast(U* value) { return dynamic_cast<T>(value); }
struct CreatureObject {
    std::array<int, 9> damage{};
    std::array<int, 3> message{};
    bool dead = false, visible = true, entryAllowed = true;
    int notifications = 0, tefChecks = 0;
    bool hasDamage(int attribute) { return damage[attribute] > 0; }
    bool isDead() { return dead; }
    bool isPlayerCreature() { return true; }
    int healDamage(CreatureObject*, int attribute, int power, bool = true, bool notify = true) {
        int healed = std::min(damage[attribute], power);
        damage[attribute] -= healed;
        if (notify) ++notifications;
        return healed;
    }
};
struct CollisionManager {
    static bool checkLineOfSight(CreatureObject*, CreatureObject* target) { return target->visible; }
};
struct PlayerManager { void sendBattleFatigueMessage(CreatureObject*, CreatureObject*) {} };
struct ZoneServer {
    PlayerManager manager;
    PlayerManager* getPlayerManager() { return &manager; }
};
struct ZoneProcessServer {
    ZoneServer zoneServer;
    ZoneServer* getZoneServer() { return &zoneServer; }
};
struct StimPack {
    Vector<byte> attributes;
    virtual ~StimPack() = default;
    virtual bool isRangedStimPack() { return false; }
    Vector<byte> getAttributes() { return attributes; }
};
struct RangedStimPack : StimPack {
    bool isRangedStimPack() override { return true; }
    uint32 calculatePower(CreatureObject*, CreatureObject*) { return 125; }
};
class HealDamageCommand {
public:
    ZoneProcessServer* server;
    bool playerEntryCheck(CreatureObject*, CreatureObject* target) const { return target->entryAllowed; }
    void sendHealMessage(CreatureObject*, CreatureObject* target, int health, int action, int mind) const {
        target->message = {health, action, mind};
    }
    void awardXp(CreatureObject*, const String&, int) const {}
    void checkForTef(CreatureObject*, CreatureObject* target) const { ++target->tefChecks; }
'''
    for signature in ("bool checkTarget(", "void doAreaMedicActionTarget("):
        cpp += method("src/server/zone/objects/creature/commands/HealDamageCommand.h", signature)
    cpp += r'''
};
int main() {
    ZoneProcessServer server;
    HealDamageCommand command{&server};
    CreatureObject healer, patient;
    patient.damage[CreatureAttribute::MIND] = 200;
    assert(command.checkTarget(&healer, &patient));
    assert(command.checkTarget(&patient, &patient));
    patient.visible = false;
    assert(!command.checkTarget(&healer, &patient));
    patient.visible = true;
    patient.entryAllowed = false;
    assert(!command.checkTarget(&healer, &patient));
    patient.entryAllowed = true;
    patient.dead = true;
    assert(!command.checkTarget(&healer, &patient));
    patient.dead = false;
    patient.damage.fill(0);
    assert(!command.checkTarget(&healer, &patient));
'''
    for name, attributes, ranged in templates:
        if not ranged:
            continue
        cpp += "{ RangedStimPack stim; stim.attributes = {" + ",".join(map(str, attributes)) + "};\n"
        cpp += r'''
    patient.damage.fill(0);
    patient.damage[CreatureAttribute::MIND] = 200;
    patient.notifications = 0;
    assert(command.checkTarget(&healer, &patient));
    command.doAreaMedicActionTarget(&healer, &patient, &stim);
    assert(patient.damage[CreatureAttribute::MIND] == 75);
    assert((patient.message == std::array<int, 3>{0, 0, 125}));
    assert(patient.notifications == 1);
    patient.damage[CreatureAttribute::HEALTH] = 200;
    patient.damage[CreatureAttribute::ACTION] = 200;
    patient.damage[CreatureAttribute::MIND] = 200;
    command.doAreaMedicActionTarget(&healer, &patient, &stim);
    assert((patient.message == std::array<int, 3>{125, 125, 125}));
'''
        cpp += "std::cout << " + json.dumps(name + " passed.\n") + "; }\n"
    cpp += '}\n'
    with tempfile.TemporaryDirectory(prefix="solo_stimpack_") as tmp:
        tmp = Path(tmp)
        source = tmp / "stimpack.cpp"
        source.write_text(cpp, encoding="utf-8")
        executable = tmp / "stimpack_test.exe"
        if Path(args.compiler).stem.lower() == "cl":
            command = [args.compiler, "/nologo", "/EHsc", "/std:c++17", str(source),
                       "/Fe:" + str(executable), "/Fo:" + str(tmp / "stimpack.obj")]
        else:
            command = [args.compiler, "-std=c++17", str(source), "-o", str(executable)]
        subprocess.run(command, check=True)
        subprocess.run([str(executable)], check=True)
    print(f"All {len(templates)} stimpack definitions and Mind-only area healing passed.")


if __name__ == "__main__":
    main()
