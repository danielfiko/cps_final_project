import r2 as rem
import time
import threading, queue
from mirobot import Mirobot


red_placement_area_free = True                      # Bestemmer om rødt plasseringsområdet er opptatt
waiting = [False, False]                            # Kø for robotene som vil plukke rød kloss
next_turn = None                                    # Bestemmer hvem som er neste til å plukke rød kloss


class Robot:

    def __init__(self, bot_id):                     # Oppretter Robot-objekt (1 per robot)
        self.bot_id = bot_id                        # ID-nummer på boten
        self.red_cubes = []                         # Liste med alle røde kuber
        self.other_cubes = []                       # Liste med alle grønne og blå kuber
        self.red_cubes_placed = 0                   # Teller antall røde kuber plassert
        self.other_cubes_placed = 0                 # (for å flytte posisjonen hvor neste kube blir plassert)
        self.first = True                           # Angir om det er første runde roboten blir kjørt
        self.ready_to_place = False                 # Angir om roboten har plukket rød kloss og venter på å slippe den
        self.cam = rem.remote_control()             # Oppretter remote control objekt av r2.py
        if bot_id == 1:                             # Setter robot- og kameraport for bot 1
            self.port = "/dev/ttyUSB_Mirobot1"
            self.bot = Mirobot(portname=self.port, debug=False)
            self.cam_port = self.cam.get_camera(self.cam.CAMERA_ONE_PORT)
        if bot_id == 2:                             # Setter robot- og kameraport for bot 2
            self.port = "/dev/ttyUSB_Mirobot2"
            self.bot = Mirobot(portname=self.port, debug=False)
            self.cam_port = self.cam.get_camera(self.cam.CAMERA_TWO_PORT)

    def initialize(self):                           # Kjører initsialisering av roboten og starter plukkefunksjonen
        self.bot.home_simultaneous()
        self.start_picking()

    def start_picking(self):
        while True:#self.first or len(self.red_cubes) + len(self.other_cubes) > 0:
            global red_placement_area_free, waiting, next_turn  # Angir at disse skal være globale så begge trådene
                                                                # kan dele de.
            if self.red_cubes:
                    waiting[self.bot_id-1] = True               # Setter roboten i kø for å plukke rød kloss
                    if next_turn == None:                       # Setter at boten er neste til å plukke rød
                        next_turn = self.bot_id
            if self.ready_to_place and not red_placement_area_free: # Hopper over resten av koden hvis roboten venter
                continue
            if self.red_cubes and red_placement_area_free and next_turn == self.bot_id: # Plukker rød kloss
                red_placement_area_free = False                 # Sier at rød område er opptatt
                waiting[self.bot_id-1] = False                  # Fjerner roboten fra kø til å plukke røde klosser
                self.pick_and_place_cube(self.red_cubes[0], self.red_cubes_placed, not self.ready_to_place)
                self.red_cubes_placed += 1                      # Øker antall plasserte røde klosser
                self.red_cubes.pop(0)                           # Fjerner klossen fra lista
                self.ready_to_place = False
                red_placement_area_free = True
                if waiting[self.bot_id % 2]:                    # Sjekker hvem som skal plukke rød neste runde
                    next_turn = (self.bot_id % 2) + 1
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!")
                elif self.red_cubes:
                    next_turn = self.bot_id
                else:
                    next_turn = None
                print("Next turn: ", str(next_turn))
            elif self.other_cubes:                              # Plukke grønn eller blå kloss
                print(str(self.bot_id), " placing g/b cube")
                self.pick_and_place_cube(self.other_cubes[0], self.other_cubes_placed)
                self.other_cubes_placed += 1
                self.other_cubes.pop(0)
            if waiting[self.bot_id-1] and not self.ready_to_place:  # Plukker rød kloss og venter ved kanten av rødt område
                self.pick_and_place_cube(self.red_cubes[0], self.red_cubes_placed, True, False)
                self.ready_to_place = True
            if not self.red_cubes:                                  # Hvis det ikke er noen røde klosser i lista
                print(str(self.bot_id), " getting blob data")       # ta nytt bilde
                if self.first:
                    self.move_for_camera(True)                      # flytter armen hvis det er første runde
                    self.first = False
                self.get_blob_data()
                if len(self.red_cubes) + len(self.other_cubes) == 0: # Venter ett sekund hvis robotarmen ikke gjør noe
                    time.sleep(1)                                    # (ingen klosser i lista)

    def pick_and_place_cube(self, cube, placed_cubes, ready_to_pick=True, place=True):
        z = dz = 8                                                  # Setter z-verdien (høyden over plata)
        rx = ry = rz = 0                                            # Sier at den ikke skal rotere noe (beholde vinkelen)
        speed = 2000                                                # Farta den beveger seg
        is_cube = True                                              # Aner ikke hva dette er, kopierte bare fra APIet
        initial_x = 160                                             # Posisjon til første kloss som plukkes
        initial_y = -120
        self.x = cube[5]                                            # Henter posisjonen klossen skal plukkes fra
        self.y = cube[6]
        self.place_x = initial_x + (placed_cubes * 30)              # Setter X-verdien klossen skal plasseres
        self.place_y = initial_y                                    # (flyttes 30 verdier frem for hver kloss
                                                                    # så de havner på en rekke)
        if cube[4] == "Red":
            self.place_y = initial_y * -1                           # Inverterer Y-koordinatet så rød klosser kommer
                                                                    # på motsatt side
        try:
            self.bot.unlock_shaft()                                 # Funksjonene som utfører bevegelsene til roboten
            if ready_to_pick:
                self.bot.go_to_cartesian_lin(self.x, self.y, z + 10, rx, ry, rz, speed)  # Move above cube
                self.bot.go_to_cartesian_lin(self.x, self.y, z, rx, ry, rz, speed) # Move down to cube
                self.bot.send_msg('M3S1000') # Suction cup on
                self.bot.go_to_cartesian_lin(self.x, self.y, z + 30, rx, ry, rz, speed)  # Move up
            if ready_to_pick and not place:                         # Flytter seg til kanten av rødt plasseringsområde
                self.bot.go_to_cartesian_lin(self.place_x, 90, dz + 30, rx, ry, rz, speed)  # Move to above drop off coordinate
            if place:                                               # Plasserer klossen
                self.bot.go_to_cartesian_lin(self.place_x, self.place_y, dz + 30, rx, ry, rz, speed)  # Move to above drop off coordinate
                self.bot.go_to_cartesian_lin(self.place_x, self.place_y, dz, rx, ry, rz, speed)  # Move down to drop off coordinate
                self.bot.send_msg('M3S0') # Suction cup off
                self.bot.go_to_cartesian_lin(self.place_x, self.place_y, dz + 10, rx, ry, rz, speed)  # Move up from cube
                if self.place_y >= 120:                             # Flytter armen ut av rødt plasseringsområde
                    self.bot.go_to_cartesian_lin(self.place_x, 90, dz + 10, rx, ry, rz, speed)  # Move out of red placement area
        except KeyboardInterrupt:                                   # Stopper roboten hvis vi trykker CTRL + C
            print()
            print("You sucessfully stopped the robot.")
            print("Press the reset button to end the prograbot.")
            print("Home the robot before further operations.")
            print()
            self.bot.send_msg('!')

    def get_blob_data(self):                                        # Tar bilde og putter kuber i listene
        self.cam.fill_data_list(self.cam_port)                      # Tar bilde og returnerer data, endret loopen
                                                                    # i denne funksjonen fra 25 til 2 runder
                                                                    # som gjør at den kjører MYE raskere
        self.red_cubes.clear()                                      # Tømmer listen med røde kuber
        self.other_cubes.clear()                                    # Tømmer listen med grønne og blå kuber
        count = 0
        for i in range(len(self.cam.prev_cx)):                      # Teller hvor mange kuber det er totalt
            if self.cam.prev_cx[i] != -1:
                count = count + 1
        blobs = [-1] * count                                        # Lager array for antall kuber med verdi -1
        tag_corners = self.cam.get_tag_corners()                    # Gjør noe i APIet (jeg vet ikke hva)

        for i in range(len(self.cam.prev_cx)):                      # Putter inn verdier for hver kloss i blobs[]
            if self.cam.prev_cx[i] != -1:
                cx = self.cam.prev_cx[i]
                cy = self.cam.prev_cy[i]
                area = self.cam.prev_area[i]
                rotation = self.cam.prev_rotation_angle[i]
                color = self.cam.color[i]
                is_cube = self.cam.is_cube_list[i]
                cx_robot_frame, cy_robot_frame = self.cam.rescale(cx, cy, tag_corners, self.bot_id)
                blob_tuple = [cx, cy, area, rotation, color, int(cx_robot_frame), int(cy_robot_frame), is_cube]
                blobs[i] = blob_tuple

        #self.cam.draw(self.cam.prev_cx, self.cam.prev_cy)          # Tegner koordinatene til klossene i terminalvinduet
        
        for cube in blobs:                                          # Sorterer kloassene i røde og grønne/blå listene
            if abs(cube[6]) <= 90:                                  # Tar kun med klosser på innsiden av April taggene
                if cube[4] == "Red":
                    self.red_cubes.append(cube)
                else:
                    self.other_cubes.append(cube)

        sorted_list = sorted(blobs, key=lambda k: k[4], reverse=True)   # Sorterer klosser i rekkefølgen på X-aksen
        print("Bot ", self.bot_id, " cubes:")
        for i in range(len(sorted_list)):                               # Printer ut liste med alle klossene
            count = i + 1
            print(str(count) + ": " + str(sorted_list[i]))
        
        # clears all previous cubes                                     # Nullstiller alle variablene fill_data_list
        sorted_list.clear()                                             # bruker for at gamle klosser ikke skal dukke
        blobs.clear()                                                   # på nytt når vi tar nye bilder. Det er en egen
        print(sorted_list)                                              # funksjon, clear_data_list, men den funker ikke
        self.cam.prev_cx = [-1] * 25
        self.cam.prev_cx = [-1] * 25
        self.cam.prev_cy = [-1] * 25
        self.cam.prev_area = [-1] * 25
        self.cam.prev_rotation_angle = [-1] * 25
        self.cam.color = []
        self.cam.is_cube_list = []
        self.cam.april_tags = {}


    def move_for_camera(self, away):                                    # Flytter armen til siden for å ikke være i
        rot_degrees = 60                                                # veien for kameraet første gangen vi tar bilde,
        if away:                                                        # de andre gangene tas bilde mens armen setter
            rot_degrees = -60                                           # ned en kloss.
        try:
            self.bot.unlock_shaft()
            self.bot.go_to_axis(rot_degrees, 0, 0, 0, 0, 0, 0, 2000)
        except KeyboardInterrupt:
            print()
            print("You sucessfully stopped the robot.")
            print("Press the reset button to end the prograbot.")
            print("Home the robot before further operations.")
            print()
            self.bot.send_msg('!')


bot1 = Robot(1)                                                         # Oppretter robot-objektene
bot2 = Robot(2)
thread_1 = threading.Thread(target=bot1.initialize)                     # Definerer trådene og hvilke funksjon som skal starte
thread_2 = threading.Thread(target=bot2.initialize)
thread_1.start()                                                        # Starter trådene
thread_2.start()
