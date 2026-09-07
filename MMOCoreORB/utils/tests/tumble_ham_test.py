"""Compile all three production tumble commands and check their full HAM cost.

Requires Python and a C++17 compiler. This does not replace a full Core3 build.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

CORE = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()
    cpp = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <string>
using uint64 = uint64_t;
using String = std::string;
using UnicodeString = String;
namespace CreatureAttribute { enum { HEALTH = 0, STRENGTH = 1, ACTION = 3, QUICKNESS = 4, MIND = 6, FOCUS = 7 }; }
namespace CreaturePosture { enum { UPRIGHT, CROUCHED, PRONE, INCAPACITATED }; }
namespace CreatureState { enum { TUMBLING }; }
unsigned int STRING_HASHCODE(const char* value) { return String(value) == "tumble" ? 1 : 2; }
struct System { static int random(int) { return 0; } };
template<class T> struct Reference {
    T ptr;
    Reference(T value = nullptr) : ptr(value) {}
    T operator->() const { return ptr; }
    operator T() const { return ptr; }
    template<class U> U castTo() const { return static_cast<U>(ptr); }
};
struct Locker { template<class T> explicit Locker(T) {} void release() {} };
struct CreatureObject;
struct StateBuff {
    StateBuff(CreatureObject*, int, int) {}
    void setSkillModifier(const String&, int) {}
};
struct CreatureObject {
    std::array<int, 9> ham{2500, 300, 300, 2500, 300, 300, 2500, 300, 300};
    bool stateAllowed = true, locomotionAllowed = true, dizzy = false, dizzyEvent = false;
    int posture = CreaturePosture::UPRIGHT;
    int animations = 0, animation = 0, buffs = 0, destructionEvents = 0, updates = 0;
    CreatureObject* animationTarget = nullptr;
    int getHAM(int attribute) const { return ham[attribute]; }
    float calculateCostAdjustment(int attribute, float cost) const {
        return std::max(0.f, cost - ((getHAM(attribute) - 300) / 1200.f) * cost);
    }
    void setHAM(int attribute, int value, bool notify = true) {
        assert(notify);
        ham[attribute] = value;
        ++updates;
    }
    int notifyObjectDestructionObservers(CreatureObject* attacker, int condition, bool combat) {
        assert(attacker == this && condition == 0 && !combat);
        assert(ham[0] == 0 && ham[3] == 0 && ham[6] == 0);
        assert(!dizzyEvent);
        ++destructionEvents;
        posture = CreaturePosture::INCAPACITATED;
        return 1;
    }
    int inflictDamage(CreatureObject*, int attribute, float damage, bool destroy) {
        if (posture == CreaturePosture::INCAPACITATED) return 0;
        ham[attribute] = std::max(destroy ? 0 : 1, ham[attribute] - static_cast<int>(damage));
        if (ham[attribute] == 0) { ++destructionEvents; posture = CreaturePosture::INCAPACITATED; }
        return 0;
    }
    void setPosture(int value, bool, bool) { assert(destructionEvents == 0); posture = value; }
    void doCombatAnimation(CreatureObject* target, unsigned int value, int, int) {
        assert(destructionEvents == 0);
        ++animations; animation = value; animationTarget = target;
    }
    bool isDizzied() { return dizzy; }
    void queueDizzyFallEvent() { dizzyEvent = true; }
    void clearDizzyEvent() { dizzyEvent = false; }
    void addBuff(StateBuff* buff) { ++buffs; delete buff; }
    void sendStateCombatSpam(const String&, const String&, int) {}
};
struct ZoneServer {
    CreatureObject* target = nullptr;
    Reference<CreatureObject*> getObject(uint64) { return target; }
};
struct ZoneProcessServer { ZoneServer zone; ZoneServer* getZoneServer() { return &zone; } };
struct QueueCommand {
    enum { SUCCESS, INVALIDSTATE, INVALIDLOCOMOTION, INSUFFICIENTHAM };
    ZoneProcessServer* server;
    QueueCommand(const String&, ZoneProcessServer* value) : server(value) {}
    bool checkStateMask(CreatureObject* creature) const { return creature->stateAllowed; }
    bool checkInvalidLocomotions(CreatureObject* creature) const { return creature->locomotionAllowed; }
};
'''
    commands = CORE / "src/server/zone/objects/creature/commands"
    for name in ("TumbleToKneelingCommand.h", "TumbleToProneCommand.h", "TumbleToStandingCommand.h"):
        cpp += "\n".join(line for line in (commands / name).read_text().splitlines()
                         if not line.startswith("#include")) + "\n"
    cpp += r'''
template<class Command> void checkCommand() {
    ZoneProcessServer server;
    Command command("tumble", &server);
    for (int secondary : {300, 2500}) {
        for (const auto& pools : {std::array<int, 3>{2500, 2500, 2500}, {23, 47, 61}, {1, 1, 1}}) {
            for (bool dizzy : {false, true}) {
                CreatureObject creature, target;
                creature.ham[0] = pools[0]; creature.ham[3] = pools[1]; creature.ham[6] = pools[2];
                creature.ham[1] = creature.ham[4] = creature.ham[7] = secondary;
                creature.dizzy = dizzy;
                creature.dizzyEvent = true; // Also cancel a fall queued before the tumble.
                const auto previous = creature.ham;
                server.zone.target = dizzy ? &target : nullptr;
                assert(command.doQueueCommand(&creature, 42, "") == QueueCommand::SUCCESS);
                assert(creature.ham[0] == 0 && creature.ham[3] == 0 && creature.ham[6] == 0);
                for (int index : {1, 2, 4, 5, 7, 8}) assert(creature.ham[index] == previous[index]);
                assert(creature.destructionEvents == 1 && creature.updates == 3);
                assert(creature.posture == CreaturePosture::INCAPACITATED && !creature.dizzyEvent);
                assert(creature.animations == 1 && creature.animation == (dizzy ? 2 : 1));
                assert(creature.animationTarget == (dizzy ? &target : &creature));
                assert(command.doQueueCommand(&creature, 42, "") == QueueCommand::INSUFFICIENTHAM);
                assert(creature.destructionEvents == 1 && creature.animations == 1);
            }
        }
    }
    for (int empty : {0, 3, 6}) {
        CreatureObject creature;
        creature.ham[empty] = 0;
        const auto previous = creature.ham;
        assert(command.doQueueCommand(&creature, 0, "") == QueueCommand::INSUFFICIENTHAM);
        assert(creature.ham == previous && creature.animations == 0 && creature.destructionEvents == 0);
    }
    for (bool stateFailure : {false, true}) {
        CreatureObject creature;
        creature.stateAllowed = !stateFailure;
        creature.locomotionAllowed = stateFailure;
        const auto previous = creature.ham;
        assert(command.doQueueCommand(&creature, 0, "") ==
               (stateFailure ? QueueCommand::INVALIDSTATE : QueueCommand::INVALIDLOCOMOTION));
        assert(creature.ham == previous && creature.animations == 0 && creature.destructionEvents == 0);
    }
}
int main() {
    checkCommand<TumbleToKneelingCommand>();
    checkCommand<TumbleToProneCommand>();
    checkCommand<TumbleToStandingCommand>();
    std::cout << "All three tumble commands: full HAM drain, single incapacitation notification, dizzy cancellation and failed-command checks passed.\n";
}
'''
    with tempfile.TemporaryDirectory(prefix="solo_tumble_") as tmp:
        tmp = Path(tmp)
        source = tmp / "tumble.cpp"
        source.write_text(cpp, encoding="utf-8")
        executable = tmp / "tumble_test.exe"
        if Path(args.compiler).stem.lower() == "cl":
            command = [args.compiler, "/nologo", "/EHsc", "/std:c++17", str(source),
                       "/Fe:" + str(executable), "/Fo:" + str(tmp / "tumble.obj")]
        else:
            command = [args.compiler, "-std=c++17", str(source), "-o", str(executable)]
        subprocess.run(command, check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
