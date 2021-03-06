import mock
import numpy as np
import os
import sys
import unittest

from analysis_engine.node import (
    A, KeyTimeInstance, KTI, load, Parameter, P, Section, S, M)

from analysis_engine.flight_phase import Climbing

from analysis_engine.key_time_instances import (
    AltitudePeak,
    AltitudeWhenClimbing,
    AltitudeWhenDescending,
    APDisengagedSelection,
    APEngagedSelection,
    ATDisengagedSelection,
    ATEngagedSelection,
    Autoland,
    BottomOfDescent,
    ClimbStart,
    ClimbThrustDerateDeselected,
    EngFireExtinguisher,
    EngStart,
    EngStop,
    EnterHold,
    ExitHold,
    FirstFlapExtensionWhileAirborne,
    FlapExtensionWhileAirborne,
    FlapLeverSet,
    FlapAlternateArmedSet,
    FlapLoadReliefSet,
    FlapRetractionWhileAirborne,
    FlapRetractionDuringGoAround,
    GearDownSelection,
    GearUpSelection,
    GearUpSelectionDuringGoAround,
    GoAround,
    InitialClimbStart,
    LandingDecelerationEnd,
    LandingStart,
    LandingTurnOffRunway,
    Liftoff,
    LocalizerEstablishedEnd,
    LocalizerEstablishedStart,
    LowestAltitudeDuringApproach,
    MinsToTouchdown,
    OffBlocks,
    OnBlocks,
    SecsToTouchdown,
    SlatAlternateArmedSet,
    SpeedbrakeOpen,
    TakeoffAccelerationStart,
    TakeoffPeakAcceleration,
    TakeoffTurnOntoRunway,
    TAWSGlideslopeCancelPressed,
    TAWSTerrainOverridePressed,
    TAWSMinimumsTriggered,
    TopOfClimb,
    TopOfDescent,
    TouchAndGo,
    Touchdown,
    Transmit,
    VNAVModeAndEngThrustModeRequired,
)

from flight_phase_test import buildsection, buildsections

debug = sys.gettrace() is not None

test_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'test_data')

##############################################################################
# Superclasses


class NodeTest(object):

    def test_can_operate(self):
        self.assertEqual(
            self.node_class.get_operational_combinations(),
            self.operational_combinations,
        )


##############################################################################


class TestAltitudePeak(unittest.TestCase):
    def setUp(self):
        self.alt_aal = P(name='Altitude AAL', array=np.ma.array([
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
            5, 5, 4, 4, 3, 3, 2, 2, 1, 1,
        ]))

    def test_can_operate(self):
        expected = [('Altitude AAL',)]
        self.assertEqual(AltitudePeak.get_operational_combinations(), expected)

    def test_derive(self):
        alt_peak = AltitudePeak()
        alt_peak.derive(self.alt_aal)
        expected = [KeyTimeInstance(name='Altitude Peak', index=9)]
        self.assertEqual(alt_peak, expected)


class TestBottomOfDescent(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Climb Cruise Descent','Airborne')]
        opts = BottomOfDescent.get_operational_combinations()
        self.assertEqual(opts, expected) 
        
    def test_bottom_of_descent_basic(self):
        testwave = np.cos(np.arange(0,6.3,0.1))*(2500)+2560
        alt_std = Parameter('Altitude STD Smoothed', np.ma.array(testwave))
        from analysis_engine.flight_phase import ClimbCruiseDescent
        ccd = ClimbCruiseDescent()
        air = buildsection('Airborne', 0,50)
        ccd.derive(alt_std)
        bod = BottomOfDescent()
        bod.derive(ccd, air)    
        expected = [KeyTimeInstance(index=31, name='Bottom Of Descent')]
        self.assertEqual(bod, expected)

    def test_bottom_of_descent_complex(self):
        airs = buildsections('Airborne', [896, 1654], [1688, 2055])
        ccds = buildsections('Climb Cruise Descent', [897, 1253], [1291, 1651], [1689, 2054])
        bod = BottomOfDescent()
        bod.derive(ccds, airs)    
        expected = [KeyTimeInstance(index=1253, name='Bottom Of Descent'),
                    KeyTimeInstance(index=1651, name='Bottom Of Descent'),
                    KeyTimeInstance(index=2054, name='Bottom Of Descent')]        
        self.assertEqual(bod, expected)

    def test_bod_air_only(self):
        air = buildsection('Airborne', 0,51)
        bod = BottomOfDescent()
        bod.derive(None, air)    
        expected = [KeyTimeInstance(index=51, name='Bottom Of Descent')]        
        self.assertEqual(bod, expected)
        
    def test_bod_ccd_only(self):
        ccds = buildsection('Climb Cruise Descent', 897, 1253)
        bod = BottomOfDescent()
        bod.derive(ccds, None)    
        expected = [KeyTimeInstance(index=1253, name='Bottom Of Descent')]        
        self.assertEqual(bod, expected)
        

class TestClimbStart(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Altitude AAL', 'Liftoff', 'Top Of Climb')]
        opts = ClimbStart.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_climb_start_basic(self):
        #vert_spd = Parameter('Vertical Speed', np.ma.array([1200]*8))
        #climb = Climbing()
        #climb.derive(vert_spd, [Section('Fast',slice(0,8,None),0,8)])
        alt_aal = Parameter('Altitude AAL', np.ma.array(range(0,1600,220)))
        liftoffs = KTI('Liftoff', items=[KeyTimeInstance(0, 'Liftoff')])
        tocs = KTI('Top Of Climb',
                   items=[KeyTimeInstance(len(alt_aal.array) - 1, 'Top Of Climb')])
        kti = ClimbStart()
        kti.derive(alt_aal, liftoffs, tocs)
        # These values give an result with an index of 4.5454 recurring.
        expected = [KeyTimeInstance(index=5/1.1, name='Climb Start')]
        self.assertEqual(len(kti), 1)
        self.assertAlmostEqual(kti[0].index, 4.5, 1)
    
    def test_climb_start_slow_climb(self):
        # Failed when ClimbStart was based on Climbing.
        alt_aal = load(os.path.join(test_data_path,
                                    'ClimbStart_AltitudeAAL_1.nod'))
        liftoffs = load(os.path.join(test_data_path,
                                    'ClimbStart_Liftoff_1.nod'))
        tocs = load(os.path.join(test_data_path,
                                 'ClimbStart_TopOfClimb_1.nod'))
        kti = ClimbStart()
        kti.derive(alt_aal, liftoffs, tocs)
        self.assertEqual(len(kti), 1)
        self.assertAlmostEqual(kti[0].index, 1384, 0)


class TestClimbThrustDerateDeselected(unittest.TestCase):
    def test_can_operate(self):
        expected = [('AT Climb 1 Derate', 'AT Climb 2 Derate')]
        opts = ClimbThrustDerateDeselected.get_operational_combinations()
        self.assertEqual(opts, expected)
    
    def test_derive_basic(self):
        values_mapping = {0: 'Not Latched', 1: 'Latched'}
        climb_derate_1 = M('AT Climb 1 Derate',
                           array=np.ma.array([0,0,1,1,0,0,0,1,0,0]),
                           values_mapping=values_mapping)
        climb_derate_2 = M('AT Climb 2 Derate',
                           array=np.ma.array([0,0,0,1,1,0,0,0,0,0]),
                           values_mapping=values_mapping)
        node = ClimbThrustDerateDeselected()
        node.derive(climb_derate_1, climb_derate_2)
        self.assertEqual(node, [KeyTimeInstance(index=4.5, name='Climb Thrust Derate Deselected'),
                                KeyTimeInstance(index=7.5, name='Climb Thrust Derate Deselected')])


class TestGoAround(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(GoAround.get_operational_combinations(),
                    [('Descent Low Climb', 'Altitude AAL For Flight Phases'),
                     ('Descent Low Climb', 'Altitude AAL For Flight Phases',
                      'Altitude Radio')])

    def test_go_around_basic(self):
        dlc = [Section('Descent Low Climb',slice(10,18),10,18)]
        alt = Parameter('Altitude AAL',\
                        np.ma.array(range(0,4000,500)+\
                                    range(4000,0,-500)+\
                                    range(0,1000,501)))
        goa = GoAround()
        # Pretend we are flying over flat ground, so the altitudes are equal.
        goa.derive(dlc,alt,alt)
        expected = [KeyTimeInstance(index=16, name='Go Around')]
        self.assertEqual(goa, expected)

    def test_multiple_go_arounds(self):
        # This tests for three go-arounds, but the fourth part of the curve
        # does not produce a go-around as it ends in mid-descent.
        alt = Parameter('Altitude AAL',
                        np.ma.array(np.cos(
                            np.arange(0,21,0.02))*(1000)+2500))
        ####if debug:
        ####    from analysis_engine.plot_flight import plot_parameter
        ####    plot_parameter(alt.array)
            
        dlc = buildsections('Descent Low Climb',[50,260],[360,570],[670,890])
        
        ## Merge with analysis_engine refactoring
            #from analysis_engine.plot_flight import plot_parameter
            #plot_parameter(alt)
            
        #aal = ApproachAndLanding()
        #aal.derive(Parameter('Altitude AAL For Flight Phases',alt),
                   #Parameter('Altitude Radio For Flight Phases',alt))
            
        #climb = ClimbForFlightPhases()
        #climb.derive(Parameter('Altitude STD Smoothed', alt), 
                     #[Section('Fast',slice(0,len(alt),None))])
        
        goa = GoAround()
        goa.derive(dlc,alt,alt)
                   
        expected = [KeyTimeInstance(index=157, name='Go Around'), 
                    KeyTimeInstance(index=471, name='Go Around'), 
                    KeyTimeInstance(index=785, name='Go Around')]
        self.assertEqual(goa, expected)

    def test_go_around_no_rad_alt(self):
        # This tests that the go-around works without a radio altimeter.
        dlc = [Section('Descent Low Climb',slice(10,18),10,18)]
        alt = Parameter('Altitude AAL',\
                        np.ma.array(range(0,4000,500)+\
                                    range(4000,0,-500)+\
                                    range(0,1000,501)))
        goa = GoAround()
        # Pretend we are flying over flat ground, so the altitudes are equal.
        goa.derive(dlc,alt,None)
        expected = [KeyTimeInstance(index=16, name='Go Around')]
        self.assertEqual(goa, expected)


    def test_go_around_with_rad_alt(self):
        # This tests that the go-around works without a radio altimeter.
        alt = Parameter('Altitude AAL',
                        np.ma.array(np.cos(
                            np.arange(0,21,0.02))*(1000)+2500))
        alt_rad = Parameter('Altitude Radio',\
                        alt.array-range(len(alt.array)))
        ####if debug:
        ####    from analysis_engine.plot_flight import plot_parameter
        ####    plot_parameter(alt_rad.array)
        # The sloping graph has shifted minima. We only need to check one to
        # show it's using the rad alt signal.
        dlc = [Section('Descent Low Climb',slice( 50,260),50,260)]

        goa = GoAround()
        goa.derive(dlc,alt,alt_rad)
        expected = [KeyTimeInstance(index=160, name='Go Around')]
        self.assertEqual(goa, expected)



"""
class TestAltitudeInApproach(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(AltitudeInApproach.get_operational_combinations(),
                         [('Approach', 'Altitude AAL')])
    
    def test_derive(self):
        approaches = S('Approach', items=[Section('a', slice(4, 7)),
                                                      Section('b', slice(10, 20))])
        alt_aal = P('Altitude AAL',
                    np.ma.masked_array(range(1950, 0, -200) + \
                                       range(1950, 0, -200)))
        altitude_in_approach = AltitudeInApproach()
        altitude_in_approach.derive(approaches, alt_aal)
        self.assertEqual(list(altitude_in_approach),
          [KeyTimeInstance(index=4.75, name='1000 Ft In Approach',
                           datetime=None, latitude=None, longitude=None),
           KeyTimeInstance(index=14.75, name='1000 Ft In Approach',
                           datetime=None, latitude=None, longitude=None),
           KeyTimeInstance(index=12.25, name='1500 Ft In Approach',
                           datetime=None, latitude=None, longitude=None)])
"""

"""
class TestAltitudeInFinalApproach(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(AltitudeInFinalApproach.get_operational_combinations(),
                         [('Approach', 'Altitude AAL')])
    
    def test_derive(self):
        approaches = S('Approach',
                       items=[Section('a', slice(2, 7)),
                              Section('b', slice(10, 20))])
        alt_aal = P('Altitude AAL',
                    np.ma.masked_array(range(950, 0, -100) + \
                                       range(950, 0, -100)))
        altitude_in_approach = AltitudeInFinalApproach()
        altitude_in_approach.derive(approaches, alt_aal)
        
        self.assertEqual(list(altitude_in_approach),
          [KeyTimeInstance(index=4.5,
                           name='500 Ft In Final Approach', datetime=None,
                           latitude=None, longitude=None),
           KeyTimeInstance(index=18.512820512820511,
                           name='100 Ft In Final Approach',
                           datetime=None, latitude=None, longitude=None),
           KeyTimeInstance(index=14.5,
                           name='500 Ft In Final Approach', datetime=None,
                           latitude=None, longitude=None)])
"""

class TestAltitudeWhenClimbing(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(AltitudeWhenClimbing.get_operational_combinations(),
                         [('Climbing', 'Altitude AAL', 'Altitude STD Smoothed')])
    
    def test_derive(self):
        climbing = S('Climbing', items=[Section('a', slice(4, 10), 4, 10),
                                        Section('b', slice(12, 20), 12, 20)])
        alt_aal = P('Altitude AAL',
                    np.ma.masked_array(range(0, 200, 20) + \
                                       range(0, 200, 20),
                                       mask=[False] * 6 + [True] * 3 + \
                                            [False] * 11))
        altitude_when_climbing = AltitudeWhenClimbing()
        altitude_when_climbing.derive(climbing, alt_aal)
        self.assertEqual(list(altitude_when_climbing),
          [KeyTimeInstance(index=5.0, name='100 Ft Climbing'),
           KeyTimeInstance(index=12.5, name='50 Ft Climbing'),
           KeyTimeInstance(index=13.75, name='75 Ft Climbing'),
           KeyTimeInstance(index=15.0, name='100 Ft Climbing'),
           KeyTimeInstance(index=17.5, name='150 Ft Climbing')])


class TestAltitudeWhenDescending(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(AltitudeWhenDescending.get_operational_combinations(),
                         [('Descending','Altitude AAL', 'Altitude STD Smoothed')])

    def test_derive(self):
        descending = buildsections('Descending', [0, 10], [11, 20])
        alt_aal = P('Altitude AAL',
                    np.ma.masked_array(range(100, 0, -10),
                                       mask=[False] * 6 + [True] * 3 + [False]))
        altitude_when_descending = AltitudeWhenDescending()
        altitude_when_descending.derive(descending, alt_aal)
        self.assertEqual(list(altitude_when_descending),
          [KeyTimeInstance(index=2.5, name='75 Ft Descending'),
           KeyTimeInstance(index=5.0, name='50 Ft Descending'),
        ])


#class TestAltitudeSTDWhenDescending(unittest.TestCase):
    #def test_can_operate(self):
        #self.assertEqual(AltitudeSTDWhenDescending.get_operational_combinations(),
                         #[('Descending', 'Altitude AAL', 'Altitude STD Smoothed')])

    #def test_derive(self):
        #descending = buildsections('Descending', [0, 10], [11, 20])
        #alt_aal = P('Altitude STD',
                    #np.ma.masked_array(range(100, 0, -10),
                                       #mask=[False] * 6 + [True] * 3 + [False]))
        #altitude_when_descending = AltitudeSTDWhenDescending()
        #altitude_when_descending.derive(descending, alt_aal)
        #self.assertEqual(list(altitude_when_descending),
          #[KeyTimeInstance(index=2.5, name='75 Ft Descending'),
           #KeyTimeInstance(index=5.0, name='50 Ft Descending'),
        #])


class TestInitialClimbStart(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Takeoff',)]
        opts = InitialClimbStart.get_operational_combinations()
        self.assertEqual(opts, expected)        

    def test_initial_climb_start_basic(self):
        instance = InitialClimbStart()
        # This just needs the takeoff slice endpoint, so trivial to test
        instance.derive([Section('Takeoff',slice(0,4,None),0,3.5)])
        expected = [KeyTimeInstance(index=3.5, name='Initial Climb Start')]
        self.assertEqual(instance, expected)

class TestLandingDecelerationEnd(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Airspeed','Landing')]
        opts = LandingDecelerationEnd.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_landing_end_deceleration(self):
        landing = [Section('Landing',slice(2,40,None),2,40)]
        speed = np.ma.array([79,77.5,76,73.9,73,70.3,68.8,67.6,66.4,63.4,62.8,
                             61.6,61.9,61,60.1,56.8,53.8,49.6,47.5,46,44.5,43.6,
                             42.7,42.4,41.8,41.5,40.6,39.7,39.4,38.5,37.9,38.5,
                             38.5,38.8,38.5,37.9,37.9,37.9,37.9,37.9])
        aspd = P('Airspeed',speed)
        kpv = LandingDecelerationEnd()
        kpv.derive(aspd, landing)
        expected = [KeyTimeInstance(index=21.0, name='Landing Deceleration End')]
        self.assertEqual(kpv, expected)


class TestTakeoffPeakAcceleration(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(TakeoffPeakAcceleration.get_operational_combinations(),
                         [('Takeoff', 'Acceleration Longitudinal')])
        
    def test_takeoff_peak_acceleration_basic(self):
        acc = P('Acceleration Longitudinal',
                np.ma.array([0,0,.1,.1,.2,.1,0,0]))
        landing = [Section('Takeoff',slice(2,5,None),2,5)]
        kti = TakeoffPeakAcceleration()
        kti.derive(landing, acc)
        expected = [KeyTimeInstance(index=4, name='Takeoff Peak Acceleration')]
        self.assertEqual(kti, expected)


class TestLandingStart(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Landing',)]
        opts = LandingStart.get_operational_combinations()
        self.assertEqual(opts, expected)        

    def test_initial_landing_start_basic(self):
        instance = LandingStart()
        # This just needs the takeoff slice endpoint, so trivial to test
        instance.derive([Section('Landing',slice(66,77,None),66,77)])
        expected = [KeyTimeInstance(index=66, name='Landing Start')]
        self.assertEqual(instance, expected)


class TestLandingTurnOffRunway(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Heading Continuous','Landing','Fast')]
        opts = LandingTurnOffRunway.get_operational_combinations()
        self.assertEqual(opts, expected)        

    def test_landing_turn_off_runway_basic(self):
        instance = LandingTurnOffRunway()
        head = P('Heading Continuous', np.ma.array([0]*30))
        fast = buildsection('Fast', 0, 20)
        land = buildsection('Landing', 10, 26)
        instance.derive(head, land, fast)
        expected = [KeyTimeInstance(index=26, name='Landing Turn Off Runway')]
        self.assertEqual(instance, expected)

    def test_landing_turn_off_runway_curved(self):
        instance = LandingTurnOffRunway()
        head = P('Heading Continuous',np.ma.array([0]*70+range(20)))
        fast = buildsection('Fast',0,65)
        land = buildsection('Landing',60,87)
        instance.derive(head, land, fast)
        expected = [KeyTimeInstance(index=73, name='Landing Turn Off Runway')]
        self.assertEqual(instance, expected)

    def test_landing_turn_off_runway_curved_left(self):
        instance = LandingTurnOffRunway()
        head = P('Heading Continuous',np.ma.array([0]*70+range(20))*-1.0)
        fast = buildsection('Fast',0,65)
        land = buildsection('Landing',60,87)
        instance.derive(head, land, fast)
        expected = [KeyTimeInstance(index=73, name='Landing Turn Off Runway')]
        self.assertEqual(instance, expected)


class TestLiftoff(unittest.TestCase):
    #TODO: Extend test coverage. This algorithm was developed using lots of
    #test data and graphical inspection, but needs a formal test framework.
    def test_can_operate(self):
        self.assertTrue(('Airborne',) in Liftoff.get_operational_combinations())

    def test_liftoff_basic(self):
        # Linearly increasing climb rate with the 5 fpm threshold set between 
        # the 5th and 6th sample points.
        vert_spd = Parameter('Vertical Speed Inertial',
                             (np.ma.arange(10) - 0.5) * 40)
        # Airborne section encloses the test point.
        airs = buildsection('Airborne', 6, None)
        lift=Liftoff()
        lift.derive(vert_spd, None, None, None, None, airs, None)
        expected = [KeyTimeInstance(index=6, name='Liftoff')]
        self.assertEqual(lift, expected)
    
    def test_liftoff_no_vert_spd_detected(self):
        # Check the backstop setting.
        vert_spd = Parameter('Vertical Speed Inertial',
                             (np.ma.array([0] * 40)))
        airs = buildsection('Airborne', 6, None)
        lift=Liftoff()
        lift.derive(vert_spd, None, None, None, None, airs, None)
        expected = [KeyTimeInstance(index=6, name='Liftoff')]
        self.assertEqual(lift, expected)
    
    def test_liftoff_already_airborne(self):
        vert_spd = Parameter('Vertical Speed Inertial',
                             (np.ma.array([0] * 40)))
        airs = buildsection('Airborne', None, 10)
        lift=Liftoff()
        lift.derive(vert_spd, airs)
        expected = []
        self.assertEqual(lift, expected)
        
    
class TestTakeoffAccelerationStart(unittest.TestCase):
    def test_can_operate(self):
        self.assertEqual(\
            TakeoffAccelerationStart.get_operational_combinations(),
            [('Airspeed', 'Takeoff'),
             ('Airspeed', 'Takeoff', 'Acceleration Longitudinal')])

    def test_takeoff_acceleration_start(self):
        # This test uses the same airspeed data as the library routine test,
        # so should give the same answer!
        airspeed_data = np.ma.array(data=[37.9,37.9,37.9,37.9,37.9,37.9,37.9,
                                          37.9,38.2,38.2,38.2,38.2,38.8,38.2,
                                          38.8,39.1,39.7,40.6,41.5,42.7,43.6,
                                          44.5,46,47.5,49.6,52,53.2,54.7,57.4,
                                          60.7,61.9,64.3,66.1,69.4,70.6,74.2,
                                          74.8],
                                    mask=[1]*22+[0]*15
                                    )
        takeoff = buildsection('Takeoff',3,len(airspeed_data))
        aspd = P('Airspeed', airspeed_data)
        instance = TakeoffAccelerationStart()
        instance.derive(aspd, takeoff,None)
        self.assertLess(instance[0].index, 1.0)
        self.assertGreater(instance[0].index, 0.5)

    def test_takeoff_acceleration_start_truncated(self):
        # This test uses the same airspeed data as the library routine test,
        # so should give the same answer!
        airspeed_data = np.ma.array(data=[37.9,37.9,37.9,37.9,37.9,
                                          37.9,38.2,38.2,38.2,38.2,38.8,38.2,
                                          38.8,39.1,39.7,40.6,41.5,42.7,43.6,
                                          44.5,46,47.5,49.6,52,53.2,54.7,57.4,
                                          60.7,61.9,64.3,66.1,69.4,70.6,74.2,
                                          74.8],
                                    mask=[1]*20+[0]*15
                                    )
        takeoff = buildsection('Takeoff',3,len(airspeed_data))
        aspd = P('Airspeed', airspeed_data)
        instance = TakeoffAccelerationStart()
        instance.derive(aspd, takeoff,None)
        self.assertEqual(instance[0].index, 0.0)


class TestTakeoffTurnOntoRunway(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Heading Continuous','Takeoff','Fast')]
        opts = TakeoffTurnOntoRunway.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_takeoff_turn_onto_runway_basic(self):
        instance = TakeoffTurnOntoRunway()
        head = P('Heading Continuous',np.ma.arange(5))
        takeoff = buildsection('Takeoff',1.7,5.5)
        fast = buildsection('Fast',3.7,7)
        instance.derive(head, takeoff, fast)
        expected = [KeyTimeInstance(index=1.7, name='Takeoff Turn Onto Runway')]
        self.assertEqual(instance, expected)

    def test_takeoff_turn_onto_runway_curved(self):
        instance = TakeoffTurnOntoRunway()
        head = P('Heading Continuous',np.ma.array(range(20)+[20]*70))
        fast = buildsection('Fast',40,90)
        takeoff = buildsection('Takeoff',4,75)
        instance.derive(head, takeoff, fast)
        expected = [KeyTimeInstance(index=21.5, name='Takeoff Turn Onto Runway')]
        self.assertEqual(instance, expected)


class TestTAWSGlideslopeCancelPressed(unittest.TestCase):

    def test_basic(self):
        tgc = M('TAWS Glideslope Cancel', ['Cancel', '-', '-', 'Cancel', 'Cancel', '-', '-'],
               values_mapping={0: '-', 1: 'Cancel'})
        air = buildsection('Airborne', 2, 8)
        glide = TAWSGlideslopeCancelPressed()
        glide.derive(tgc, air)
        expected = [KeyTimeInstance(index=2.5, name='TAWS Glideslope Cancel Pressed')]
        self.assertEqual(glide, expected)


class TestTAWSMinimumsTriggered(unittest.TestCase):

    def test_basic(self):
        tto = M('TAWS Minimums Triggered',
                ['-', '-', '-', 'Minimums', 'Minimums', '-', '-'],
                values_mapping={0: '-', 1: 'Minimums'})
        air = buildsection('Airborne', 2, 8)
        glide = TAWSMinimumsTriggered()
        glide.derive(tto, air)
        expected = [KeyTimeInstance(index=2.5,
                                    name='TAWS Minimums Triggered')]
        self.assertEqual(glide, expected)


class TestTAWSTerrainOverridePressed(unittest.TestCase):

    def test_basic(self):
        tto = M('TAWS Terrain Override Pressed',
                ['-', '-', '-', 'Override', 'Override', '-', '-'],
                values_mapping={0: '-', 1: 'Override'})
        air = buildsection('Airborne', 2, 8)
        glide = TAWSTerrainOverridePressed()
        glide.derive(tto, air)
        expected = [KeyTimeInstance(index=2.5,
                                    name='TAWS Terrain Override Pressed')]
        self.assertEqual(glide, expected)


class TestTopOfClimb(unittest.TestCase):
    # Based closely on the level flight condition, but taking only the
    # outside edges of the envelope.
    def test_can_operate(self):
        expected = [('Altitude STD Smoothed','Climb Cruise Descent')]
        opts = TopOfClimb.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_top_of_climb_basic(self):
        alt_data = np.ma.array(range(0,800,100)+[800]*5+range(800,0,-100))
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfClimb()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = [KeyTimeInstance(index=8, name='Top Of Climb')]
        self.assertEqual(phase, expected)

    def test_top_of_climb_truncated_start(self):
        alt_data = np.ma.array([800]*5+range(800,0,-100))
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfClimb()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = []
        self.assertEqual(phase, expected)
        self.assertEqual(len(phase),0)

    def test_top_of_climb_truncated_end(self):
        alt_data = np.ma.array(range(0,800,100)+[800]*5)
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfClimb()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = [KeyTimeInstance(index=8, name='Top Of Climb')]
        self.assertEqual(phase, expected)
        self.assertEqual(len(phase),1)


class TestTopOfDescent(unittest.TestCase):
    # Based closely on the level flight condition, but taking only the
    # outside edges of the envelope.
    def test_can_operate(self):
        expected = [('Altitude STD Smoothed', 'Climb Cruise Descent')]
        opts = TopOfDescent.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_top_of_descent_basic(self):
        alt_data = np.ma.array(range(0,800,100)+[800]*5+range(800,0,-100))
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfDescent()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = [KeyTimeInstance(index=13, name='Top Of Descent')]
        self.assertEqual(phase, expected)

    def test_top_of_descent_truncated_start(self):
        alt_data = np.ma.array([800]*5+range(800,0,-100))
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfDescent()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = [KeyTimeInstance(index=5, name='Top Of Descent')]
        self.assertEqual(phase, expected)
        self.assertEqual(len(phase),1)

    def test_top_of_descent_truncated_end(self):
        alt_data = np.ma.array(range(0,800,100)+[800]*5)
        alt = Parameter('Altitude STD', np.ma.array(alt_data))
        phase = TopOfDescent()
        in_air = buildsection('Climb Cruise Descent',0,len(alt.array))
        phase.derive(alt, in_air)
        expected = []
        self.assertEqual(phase, expected)
        self.assertEqual(len(phase),0)


class TestTouchdown(unittest.TestCase):
    def test_can_operate(self):
        opts = Touchdown.get_operational_combinations()
        # There are eight permutations
        self.assertEqual(len(opts), 8)
        # Minimal case
        self.assertTrue(('Altitude AAL', 'Landing') in opts)
        # Maximum case
        self.assertTrue(('Acceleration Normal', 'Acceleration Longitudinal', 'Altitude AAL', 'Gear On Ground', 'Landing') in opts)
 
    def test_touchdown_with_minimum_requirements(self):
        # Test 1
        altitude = Parameter('Altitude AAL',
                             np.ma.array(data=[28, 21, 15, 10, 6, 3, 1, 0, 0,  0],
                                         mask = False))
        lands = buildsection('Landing', 2, 9)
        tdwn = Touchdown()
        tdwn.derive(None, None, altitude, None, lands)
        expected = [KeyTimeInstance(index=7, name='Touchdown')]
        self.assertEqual(tdwn, expected)

    def test_touchdown_using_alt(self):
        '''
        test to check index where altitude becomes 0 is used instead of
        inertial landing index. Gear on Ground index indicates height at 21
        feet.
        '''
        alt = load(os.path.join(test_data_path,
                                    'TestTouchdown-alt.nod'))
        gog = load(os.path.join(test_data_path,
                                    'TestTouchdown-gog.nod'))
        #FIXME: MappedArray should take values_mapping and apply it itself
        gog.array.values_mapping = gog.values_mapping
        roc = load(os.path.join(test_data_path,
                                    'TestTouchdown-roc.nod'))
        lands = buildsection('Landing', 23279, 23361)
        tdwn = Touchdown()
        tdwn.derive(None, None, alt, gog, lands)
        self.assertEqual(tdwn.get_first().index, 23292.0)

##############################################################################
# Automated Systems


class TestAPEngagedSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = APEngagedSelection
        self.operational_combinations = [('AP Engaged', 'Fast')]

    def test_derive(self):
        ap = M(
            name='AP Engaged',
            array=['-', '-', '-', 'Engaged', '-', '-', '-'],
            values_mapping={0: '-', 1: 'Engaged'},
        )
        aes = APEngagedSelection()
        fast = buildsection('Fast', 2, 5)
        aes.derive(ap, fast)
        expected = [KeyTimeInstance(index=2.5, name='AP Engaged Selection')]
        self.assertEqual(aes, expected)


class TestAPDisengagedSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = APEngagedSelection
        self.operational_combinations = [('AP Engaged', 'Fast')]

    def test_derive(self):
        ap = M(
            name='AP Engaged',
            array=['-', '-', '-', 'Engaged', '-', '-', '-'],
            values_mapping={0: '-', 1: 'Engaged'},
        )
        ads = APDisengagedSelection()
        fast = buildsection('Fast', 2, 5)
        ads.derive(ap, fast)
        expected = [KeyTimeInstance(index=3.5, name='AP Disengaged Selection')]
        self.assertEqual(ads, expected)


class TestATEngagedSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = ATEngagedSelection
        self.operational_combinations = [('AT Engaged', 'Airborne')]

    def test_derive(self):
        at = M(
            name='AT Engaged',
            array=['-', '-', '-', 'Engaged', '-', '-', '-'],
            values_mapping={0: '-', 1: 'Engaged'},
        )
        aes = ATEngagedSelection()
        air = buildsection('Airborne', 2, 5)
        aes.derive(at, air)
        expected = [KeyTimeInstance(index=2.5, name='AT Engaged Selection')]
        self.assertEqual(aes, expected)


class TestATDisengagedSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = ATEngagedSelection
        self.operational_combinations = [('AT Engaged', 'Airborne')]

    def test_derive(self):
        at = M(
            name='AT Engaged',
            array=['-', '-', '-', 'Engaged', '-', '-', '-'],
            values_mapping={0: '-', 1: 'Engaged'},
        )
        ads = ATDisengagedSelection()
        air = buildsection('Airborne', 2, 5)
        ads.derive(at, air)
        expected = [KeyTimeInstance(index=3.5, name='AT Disengaged Selection')]
        self.assertEqual(ads, expected)


##############################################################################

# Engine Start and Stop - may run into the ends of the valid recording.

class TestEngStart(unittest.TestCase):
    
    def test_can_operate(self):
        combinations = EngStart.get_operational_combinations()
        self.assertTrue(('Eng (1) N2',) in combinations)
        self.assertTrue(('Eng (2) N2',) in combinations)
        self.assertTrue(('Eng (3) N2',) in combinations)
        self.assertTrue(('Eng (4) N2',) in combinations)
        self.assertTrue(('Eng (1) N2', 'Eng (2) N2',
                         'Eng (3) N2', 'Eng (4) N2') in combinations)
        self.assertTrue(('Eng (1) N3',) in combinations)
        self.assertTrue(('Eng (2) N3',) in combinations)
        self.assertTrue(('Eng (3) N3',) in combinations)
        self.assertTrue(('Eng (4) N3',) in combinations)
        self.assertTrue(('Eng (1) N3', 'Eng (2) N3',
                         'Eng (3) N3', 'Eng (4) N3') in combinations)
    
    def test_basic(self):
        eng2 = Parameter('Eng (2) N2', np.ma.array([0,20,40,60]))
        eng1 = Parameter('Eng (1) N2', np.ma.array(data=[0,0,99,99,60,60,60], 
                                                   mask=[1,1, 1, 1, 0, 0, 0]))
        es = EngStart()
        es.derive(None, None, None, None, eng1, eng2, None, None, None, None, None, None)
        self.assertEqual(es[0].name, 'Eng (1) Start')
        self.assertEqual(es[0].index, 4)
        self.assertEqual(es[1].name, 'Eng (2) Start')
        self.assertEqual(es[1].index, 2.5)

    def test_prefer_N2(self):
        eng_N1 = Parameter('Eng (1) N1', np.ma.array([50,50,50,50]))
        eng_N2 = Parameter('Eng (1) N2', np.ma.array(data=[0,0,0,60]))
        es = EngStart()
        es.derive(eng_N1, None, None, None, eng_N2, None, None, None, None, None, None, None)
        self.assertEqual(es[0].name, 'Eng (1) Start')
        self.assertEqual(es[0].index, 2.5)
        self.assertEqual(len(es), 1)

    def test_three_spool(self):
        eng22 = Parameter('Eng (2) N2', np.ma.array([0,20,40,60, 0, 20, 40, 60]))
        eng12 = Parameter('Eng (1) N2', np.ma.array(data=[0,0,99,99,60,60,60,60], 
                                                   mask=[1,1, 1, 1, 0, 0, 0, 0]))
        eng23 = Parameter('Eng (2) N3', np.ma.array([0,40,60,60, 0, 0, 30, 60]))
        eng13 = Parameter('Eng (1) N3', np.ma.array(data=[0,0,99,99,60,60,60, 60], 
                                                   mask=[1,1, 1, 1, 0, 0, 0, 0]))
        es = EngStart()
        es.derive(None, None, None, None, eng12, eng22, None, None, eng13, eng23, None, None)
        self.assertEqual(es[0].name, 'Eng (1) Start')
        self.assertEqual(es[0].index, 4)
        self.assertEqual(es[1].name, 'Eng (2) Start')
        self.assertEqual(es[1].index, 1.5)

    def test_N1_only(self):
        eng_N1 = Parameter('Eng (1) N1', np.ma.array([0,5,10,10]))
        es = EngStart()
        es.derive(eng_N1, None, None, None, None, None, None, None, None, None, None, None)
        self.assertEqual(es[0].name, 'Eng (1) Start')
        self.assertEqual(es[0].index, 1.5)


class TestEngStop(unittest.TestCase):
    
    def test_can_operate(self):
        combinations = EngStop.get_operational_combinations()
        self.assertTrue(('Eng (1) N2',) in combinations)
        self.assertTrue(('Eng (2) N2',) in combinations)
        self.assertTrue(('Eng (3) N2',) in combinations)
        self.assertTrue(('Eng (4) N2',) in combinations)
        self.assertTrue(('Eng (1) N2', 'Eng (2) N2',
                         'Eng (3) N2', 'Eng (4) N2') in combinations)
    
    def test_basic(self):
        eng2 = Parameter('Eng (2) N2', np.ma.array([60,40,20,0]))
        eng1 = Parameter('Eng (1) N2', np.ma.array(data=[60,40,40,99,99, 0, 0], 
                                                   mask=[ 0, 0, 0, 1, 1, 1, 1]))
        es = EngStop()
        es.derive(None, None, None, None, eng1, eng2, None, None)
        self.assertEqual(es[0].name, 'Eng (1) Stop')
        self.assertEqual(es[0].index, 2)
        self.assertEqual(es[1].name, 'Eng (2) Stop')
        self.assertEqual(es[1].index, 1.5)

class TestEnterHold(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Holding',)]
        self.assertEqual(expected, EnterHold.get_operational_combinations())

    def test_derive(self):
        hold = buildsection('Holding', 2, 5)
        expected = [KeyTimeInstance(index=2, name='Enter Hold')]
        eh = EnterHold()
        eh.derive(hold)
        self.assertEqual(eh, expected)


class TestExitHold(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Holding',)]
        self.assertEqual(expected, ExitHold.get_operational_combinations())

    def test_derive(self):
        hold = buildsection('Holding', 2, 5)
        expected = [KeyTimeInstance(index=2, name='Enter Hold')]
        eh = EnterHold()
        eh.derive(hold)
        self.assertEqual(eh, expected)


##############################################################################
# Flap & Slat


class TestFlapLoadReliefSet(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapLoadReliefSet
        self.operational_combinations = [('Flap Load Relief',)]

    def test_derive(self):
        array = ['Normal'] * 3 + ['Load Relief'] * 2 + ['Normal'] * 2
        mapping = {0: 'Normal', 1: 'Load Relief'}
        flr = M('Flap Load Relief', array, values_mapping=mapping)
        node = self.node_class()
        node.derive(flr)
        expected = [KeyTimeInstance(index=2.5, name=self.node_class.get_name())]
        self.assertEqual(node, expected)


class TestFlapAlternateArmed(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapAlternateArmedSet
        self.operational_combinations = [('Flap Alternate Armed',)]

    def test_derive(self):
        array = ['-'] * 3 + ['Armed'] * 3 + ['-'] * 1
        mapping = {0: '-', 1: 'Armed'}
        faa = M('Flap Alternate Armed', array, values_mapping=mapping)
        node = self.node_class()
        node.derive(faa)
        expected = [KeyTimeInstance(index=2.5, name=self.node_class.get_name())]
        self.assertEqual(node, expected)


class TestSlatAlternateArmedSet(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = SlatAlternateArmedSet
        self.operational_combinations = [('Slat Alternate Armed',)]

    def test_derive(self):
        array = ['-'] * 2 + ['Armed'] * 3 + ['-'] * 2
        mapping = {0: '-', 1: 'Armed'}
        saa = M('Slat Alternate Armed', array, values_mapping=mapping)
        node = self.node_class()
        node.derive(saa)
        expected = [KeyTimeInstance(index=1.5, name=self.node_class.get_name())]
        self.assertEqual(node, expected)


class TestFlapLeverSet(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapLeverSet
        self.operational_combinations = [
            ('Flap Lever',),
            ('Flap Lever (Synthetic)',),
            ('Flap Lever', 'Flap Lever (Synthetic)'),
        ]
        array = np.ma.array((0, 0, 5, 5, 10, 10, 15, 10, 10, 5, 5, 0, 0, 17.5))
        mapping = {f0: str(f0) for f0 in (int(f1)
                   if float(f1).is_integer() else f1 for f1 in np.ma.unique(array))}
        self.flap_lever = M(name='Flap Lever', array=array, values_mapping=mapping)
        array = np.ma.array((1, 1, 1, 5, 5, 10, 10, 15, 10, 10, 5, 5, 1, 1))
        mapping = {f0: 'Lever %s' % i for i, f0 in enumerate(int(f1)
                   if float(f1).is_integer() else f1 for f1 in np.ma.unique(array))}
        self.flap_synth = M(name='Flap Lever (Synthetic)', array=array, values_mapping=mapping)

    def test_derive_basic(self):
        name = self.node_class.get_name()
        node = self.node_class()
        node.derive(self.flap_lever, None)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=10.5, name='Flap 0 Set'),
            KeyTimeInstance(index=1.5, name='Flap 5 Set'),
            KeyTimeInstance(index=8.5, name='Flap 5 Set'),
            KeyTimeInstance(index=3.5, name='Flap 10 Set'),
            KeyTimeInstance(index=6.5, name='Flap 10 Set'),
            KeyTimeInstance(index=5.5, name='Flap 15 Set'),
            KeyTimeInstance(index=12.5, name='Flap 17.5 Set'),
        ]))
        node = self.node_class()
        node.derive(None, self.flap_synth)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=11.5, name='Flap Lever 0 Set'),
            KeyTimeInstance(index=2.5, name='Flap Lever 1 Set'),
            KeyTimeInstance(index=9.5, name='Flap Lever 1 Set'),
            KeyTimeInstance(index=4.5, name='Flap Lever 2 Set'),
            KeyTimeInstance(index=7.5, name='Flap Lever 2 Set'),
            KeyTimeInstance(index=6.5, name='Flap Lever 3 Set'),
        ]))
        node = self.node_class()
        node.derive(self.flap_lever, self.flap_synth)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=10.5, name='Flap 0 Set'),
            KeyTimeInstance(index=1.5, name='Flap 5 Set'),
            KeyTimeInstance(index=8.5, name='Flap 5 Set'),
            KeyTimeInstance(index=3.5, name='Flap 10 Set'),
            KeyTimeInstance(index=6.5, name='Flap 10 Set'),
            KeyTimeInstance(index=5.5, name='Flap 15 Set'),
            KeyTimeInstance(index=12.5, name='Flap 17.5 Set'),
        ]))


class TestSpeedbrakeOpen(unittest.TestCase):
    
    def setUp(self):
        self.assertEqual(SpeedbrakeOpen.get_operational_combinations(),
                         [('Speedbrake',)])

    def test_basic(self):
        spdbrk = P('Speedbrake', array=np.ma.array([0]*5 +
                                                   [3]*3 +
                                                   [-1]*2 +
                                                   [45]*4 + 
                                                   [0]*3
                                                   ))
        node = SpeedbrakeOpen()
        node.derive(spdbrk)
        self.assertEqual(node, [
            KeyTimeInstance(index=5, name='Speedbrake Open'),
            KeyTimeInstance(index=10, name='Speedbrake Open'),
        ])


class TestFlapExtensionWhileAirborne(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapExtensionWhileAirborne
        self.operational_combinations = [
            ('Flap Lever', 'Airborne'),
            ('Flap Lever (Synthetic)', 'Airborne'),
            ('Flap Lever', 'Flap Lever (Synthetic)', 'Airborne'),
        ]
        array = np.ma.array((0, 0, 5, 5, 10, 10, 15, 10, 10, 5, 5, 0, 0))
        mapping = {int(f): str(f) for f in np.ma.unique(array)}
        self.flap_lever = M(name='Flap Lever', array=array, values_mapping=mapping)
        array = np.ma.array((1, 1, 1, 5, 5, 10, 10, 15, 10, 10, 5, 5, 1))
        mapping = {int(f): 'Lever %s' % i for i, f in enumerate(np.ma.unique(array))}
        self.flap_synth = M(name='Flap Lever (Synthetic)', array=array, values_mapping=mapping)

    def test_derive(self):
        airborne = buildsection('Airborne', 1, 12)
        name = self.node_class.get_name()
        node = self.node_class()
        node.derive(self.flap_lever, None, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=1.5, name=name),
            KeyTimeInstance(index=3.5, name=name),
            KeyTimeInstance(index=5.5, name=name),
        ]))
        node = self.node_class()
        node.derive(None, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=2.5, name=name),
            KeyTimeInstance(index=4.5, name=name),
            KeyTimeInstance(index=6.5, name=name),
        ]))
        node = self.node_class()
        node.derive(self.flap_lever, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=1.5, name=name),
            KeyTimeInstance(index=3.5, name=name),
            KeyTimeInstance(index=5.5, name=name),
        ]))


class TestEngFireExtinguisher(unittest.TestCase):

    def test_basic(self):
        e1f = P(name = 'Eng (1) Fire Extinguisher',
                array = np.ma.array(data=[0,0,0,0,0,0,1,0,0,0]),
                frequency=1, offset=0,)
        e2f = P(name = 'Eng (2) Fire Extinguisher',
                array = np.ma.array([0]*10),
                frequency=1, offset=0,)
        air = buildsection('Airborne', 2, 8)
        pull = EngFireExtinguisher()
        pull.derive(e1f, e2f, air)
        self.assertEqual(pull, [
            KeyTimeInstance(index=6, name='Eng Fire Extinguisher'),
            ])
        
    def test_none(self):
        e1f = P(name = 'Eng (1) Fire Extinguisher',
                array = np.ma.array(data=[0,0,0,0,0,0,0,0,0,0]),
                frequency=1, offset=0,)
        e2f = P(name = 'Eng (2) Fire Extinguisher',
                array = np.ma.array([0]*10),
                frequency=1, offset=0,)
        air = buildsection('Airborne', 2, 8)
        pull = EngFireExtinguisher()
        pull.derive(e1f, e2f, air)
        self.assertEqual(pull, [])

    def test_either(self):
        e2f = P(name = 'Eng (2) Fire Extinguisher',
                array = np.ma.array(data=[0,0,0,0,0,1,1,1,0,0]),
                frequency=1, offset=0,)
        e1f = P(name = 'Eng (1) Fire Extinguisher',
                array = np.ma.array([0]*10),
                frequency=1, offset=0,)
        air = buildsection('Airborne', 2, 8)
        pull = EngFireExtinguisher()
        pull.derive(e1f, e2f, air)
        self.assertEqual(pull, [
            KeyTimeInstance(index=5, name='Eng Fire Extinguisher'),
            ])
        
    def test_both(self):
        e1f = P(name = 'Eng (1) Fire Extinguisher',
                array = np.ma.array(data=[0,0,0,1,0,1,1,1,0,0]),
                frequency=1, offset=0,)
        e2f = P(name = 'Eng (2) Fire Extinguisher',
                array = np.ma.array(data=[0,0,0,1,1,1,1,1,0,0]),
                frequency=1, offset=0,)
        air = buildsection('Airborne', 1, 5)
        pull = EngFireExtinguisher()
        pull.derive(e1f, e2f, air)
        self.assertEqual(pull, [
            KeyTimeInstance(index=3, name='Eng Fire Extinguisher'),
            ])


class TestFirstFlapExtensionWhileAirborne(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FirstFlapExtensionWhileAirborne
        self.operational_combinations = [
            ('Flap Lever', 'Airborne'),
            ('Flap Lever (Synthetic)', 'Airborne'),
            ('Flap Lever', 'Flap Lever (Synthetic)', 'Airborne'),
        ]
        array = np.ma.array((0, 0, 5, 5, 10, 10, 15, 10, 10, 5, 5, 0, 0))
        mapping = {int(f): str(f) for f in np.ma.unique(array)}
        self.flap_lever = M(name='Flap Lever', array=array, values_mapping=mapping)
        array = np.ma.array((1, 1, 1, 5, 10, 10, 15, 10, 10, 5, 5, 1, 1))
        mapping = {int(f): 'Lever %s' % i for i, f in enumerate(np.ma.unique(array))}
        self.flap_synth = M(name='Flap Lever (Synthetic)', array=array, values_mapping=mapping)

    def test_derive(self):
        airborne = buildsection('Airborne', 1, 12)
        name = self.node_class.get_name()
        node = self.node_class()
        node.derive(self.flap_lever, None, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=1.5, name=name),
        ]))
        node = self.node_class()
        node.derive(None, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=2.5, name=name),
        ]))
        node = self.node_class()
        node.derive(self.flap_lever, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=1.5, name=name),
        ]))


class TestFlapRetractionWhileAirborne(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapRetractionWhileAirborne
        self.operational_combinations = [
            ('Flap Lever', 'Airborne'),
            ('Flap Lever (Synthetic)', 'Airborne'),
            ('Flap Lever', 'Flap Lever (Synthetic)', 'Airborne'),
        ]
        array = np.ma.array((0, 0, 5, 5, 10, 10, 15, 10, 10, 5, 5, 0, 0))
        mapping = {int(f): str(f) for f in np.ma.unique(array)}
        self.flap_lever = M(name='Flap Lever', array=array, values_mapping=mapping)
        array = np.ma.array((1, 1, 1, 5, 5, 10, 10, 15, 10, 10, 5, 5, 1))
        mapping = {int(f): 'Lever %s' % i for i, f in enumerate(np.ma.unique(array))}
        self.flap_synth = M(name='Flap Lever (Synthetic)', array=array, values_mapping=mapping)

    def test_derive(self):
        airborne = buildsection('Airborne', 2, 12)
        name = self.node_class.get_name()
        node = self.node_class()
        node.derive(self.flap_lever, None, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=6.5, name=name),
            KeyTimeInstance(index=8.5, name=name),
            KeyTimeInstance(index=10.5, name=name),
        ]))
        node = self.node_class()
        node.derive(None, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=7.5, name=name),
            KeyTimeInstance(index=9.5, name=name),
        ]))
        node = self.node_class()
        node.derive(self.flap_lever, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=6.5, name=name),
            KeyTimeInstance(index=8.5, name=name),
            KeyTimeInstance(index=10.5, name=name),
        ]))


class TestFlapRetractionDuringGoAround(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = FlapRetractionDuringGoAround
        self.operational_combinations = [
            ('Flap Lever', 'Go Around And Climbout'),
            ('Flap Lever (Synthetic)', 'Go Around And Climbout'),
            ('Flap Lever', 'Flap Lever (Synthetic)', 'Go Around And Climbout'),
        ]
        array = np.ma.array((0, 0, 5, 5, 10, 10, 15, 10, 10, 5, 5, 0, 0))
        mapping = {int(f): str(f) for f in np.ma.unique(array)}
        self.flap_lever = M(name='Flap Lever', array=array, values_mapping=mapping)
        array = np.ma.array((1, 1, 1, 5, 5, 10, 10, 15, 10, 10, 5, 5, 1))
        mapping = {int(f): 'Lever %s' % i for i, f in enumerate(np.ma.unique(array))}
        self.flap_synth = M(name='Flap Lever (Synthetic)', array=array, values_mapping=mapping)

    def test_derive(self):
        airborne = buildsection('Go Around', 2, 12)
        name = self.node_class.get_name()
        node = self.node_class()
        node.derive(self.flap_lever, None, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=6.5, name=name),
            KeyTimeInstance(index=8.5, name=name),
            KeyTimeInstance(index=10.5, name=name),
        ]))
        node = self.node_class()
        node.derive(None, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=7.5, name=name),
            KeyTimeInstance(index=9.5, name=name),
        ]))
        node = self.node_class()
        node.derive(self.flap_lever, self.flap_synth, airborne)
        self.assertEqual(node, KTI(name=name, items=[
            KeyTimeInstance(index=6.5, name=name),
            KeyTimeInstance(index=8.5, name=name),
            KeyTimeInstance(index=10.5, name=name),
        ]))


##############################################################################
# Gear


class TestGearDownSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = GearDownSelection
        self.operational_combinations = [('Gear Down Selected', 'Airborne')]
        self.gear_dn_sel = M(
            name='Gear Down Selected',
            array=['Down'] * 3 + ['Up'] * 2 + ['Down'] * 2,
            values_mapping={0: 'Up', 1: 'Down'},
        )
        self.airborne = buildsection('Airborne', 0, 7)

    def test_derive(self):
        node = GearDownSelection()
        node.derive(self.gear_dn_sel, self.airborne)
        self.assertEqual(node, [
            KeyTimeInstance(index=4.5, name='Gear Down Selection'),
        ])


class TestGearUpSelection(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = GearUpSelection
        self.operational_combinations = [('Gear Up Selected', 'Airborne', 'Go Around And Climbout')]
        self.gear_up_sel = M(
            name='Gear Up Selected',
            array=['Down'] * 3 + ['Up'] * 2 + ['Down'] * 2,
            values_mapping={0: 'Down', 1: 'Up'},
        )
        self.airborne = buildsection('Airborne', 0, 7)

    def test_normal_operation(self):
        go_arounds = buildsection('Go Around And Climbout', 6, 7)
        node = GearUpSelection()
        node.derive(self.gear_up_sel, self.airborne, go_arounds)
        self.assertEqual(node, [
            KeyTimeInstance(index=2.5, name='Gear Up Selection'),
        ])

    def test_during_go_around(self):
        go_arounds = buildsection('Go Around And Climbout', 2, 4)
        node = GearUpSelection()
        node.derive(self.gear_up_sel, self.airborne, go_arounds)
        self.assertEqual(node, [])


class TestGearUpSelectionDuringGoAround(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = GearUpSelectionDuringGoAround
        self.operational_combinations = [('Gear Up Selected', 'Go Around And Climbout')]
        self.gear_up_sel = M(
            name='Gear Up Selected',
            array=['Down'] * 3 + ['Up'] * 2 + ['Down'] * 2,
            values_mapping={0: 'Down', 1: 'Up'},
        )

    def test_normal_operation(self):
        go_arounds = buildsection('Go Around And Climbout', 6, 7)
        node = GearUpSelectionDuringGoAround()
        node.derive(self.gear_up_sel, go_arounds)
        self.assertEqual(node, [])

    def test_during_go_around(self):
        go_arounds = buildsection('Go Around And Climbout', 2, 4)
        node = GearUpSelectionDuringGoAround()
        node.derive(self.gear_up_sel, go_arounds)
        self.assertEqual(node, [
            KeyTimeInstance(index=2.5, name='Gear Up Selection During Go Around'),
        ])


##############################################################################


class TestLocalizerEstablishedEnd(unittest.TestCase):
    def test_can_operate(self):
        expected = [('ILS Localizer Established',)]
        self.assertEqual(
            expected,
            LocalizerEstablishedEnd.get_operational_combinations())

    def test_derive(self):
        ils = buildsection('ILS Localizer Established', 10, 20)
        expected = [
            KeyTimeInstance(index=20, name='Localizer Established End')]
        les = LocalizerEstablishedEnd()
        les.derive(ils)
        self.assertEqual(les, expected)


class TestLocalizerEstablishedStart(unittest.TestCase):
    def test_can_operate(self):
        expected = [('ILS Localizer Established',)]
        self.assertEqual(
            expected,
            LocalizerEstablishedStart.get_operational_combinations())

    def test_derive(self):
        ils = buildsection('ILS Localizer Established', 10, 20)
        expected = [
            KeyTimeInstance(index=10, name='Localizer Established Start')]
        les = LocalizerEstablishedStart()
        les.derive(ils)
        self.assertEqual(les, expected)


class TestLowestAltitudeDuringApproach(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = LowestAltitudeDuringApproach
        self.operational_combinations = [('Altitude AAL', 'Altitude Radio', 'Approach And Landing')]

    def test_derive(self):
        alt_aal = P(
            name='Altitude AAL',
            array=np.ma.array([5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        )
        alt_rad = P(
            name='Altitude Radio',
            array=np.ma.array([5, 5, 4, 4, 3, 3, 2, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9]),
        )
        approaches = buildsection('Approach And Landing', 2, 15)
        node = self.node_class()
        node.derive(alt_aal, alt_rad, approaches)
        self.assertEqual(node, [
            KeyTimeInstance(index=7, name='Lowest Altitude During Approach'),
        ])


class TestMinsToTouchdown(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Touchdown',)]
        self.assertEqual(
            expected,
            MinsToTouchdown.get_operational_combinations())

    def test_derive(self):
        td = [KeyTimeInstance(index=500, name='Touchdown')]
        sttd = MinsToTouchdown()
        sttd.derive(td)
        self.assertEqual(
            sttd,
            [
                KeyTimeInstance(index=200, name='5 Mins To Touchdown'),
                KeyTimeInstance(index=260, name='4 Mins To Touchdown'),
                KeyTimeInstance(index=320, name='3 Mins To Touchdown'),
                KeyTimeInstance(index=380, name='2 Mins To Touchdown'),
                KeyTimeInstance(index=440, name='1 Mins To Touchdown'),
            ]
        )


class TestSecsToTouchdown(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Touchdown',)]
        self.assertEqual(
            expected,
            SecsToTouchdown.get_operational_combinations())

    def test_derive(self):
        td = [KeyTimeInstance(index=100, name='Touchdown')]
        sttd = SecsToTouchdown()
        sttd.derive(td)
        self.assertEqual(
            sttd,
            [
                KeyTimeInstance(index=10, name='90 Secs To Touchdown'),
                KeyTimeInstance(index=70, name='30 Secs To Touchdown'),
            ]
        )


class TestAutoland(unittest.TestCase):
    def test_can_operate(self):
        expected = [('AP Channels Engaged', 'Touchdown'),
                    ('AP Channels Engaged', 'Touchdown', 'Family')]
        opts = Autoland.get_operational_combinations()
        self.assertEqual(opts, expected)

    def test_derive_autoland_dual(self):
        # test with no family
        td = [KeyTimeInstance(index=5, name='Touchdown')]
        ap = M('AP Channels Engaged',
               array=['-', '-', '-', 'Dual', 'Dual', 'Dual', '-', '-', '-'],
               values_mapping={0: '-', 1: 'Single', 2: 'Dual', 3: 'Triple'})
        node = Autoland()
        node.derive(ap, td, None)
        expected = [KeyTimeInstance(index=5, name='Autoland')]
        self.assertEqual(node, expected)
        # test with B737 Classic creates no autoland as requires Triple mode
        node = Autoland()
        node.derive(ap, td, A('Family', 'B737 Classic'))
        self.assertEqual(node, [])

    def test_derive_autoland(self):
        # simulate each of the states at touchdown using the indexes
        td = [KeyTimeInstance(index=3, name='Touchdown'),
              KeyTimeInstance(index=4, name='Touchdown'),
              KeyTimeInstance(index=5, name='Touchdown'),
              KeyTimeInstance(index=6, name='Touchdown')]
        ap = M('AP Channels Engaged',
               array=['-', '-', '-', 'Triple', 'Dual', 'Single', '-', '-', '-'],
               values_mapping={0: '-', 1: 'Single', 2: 'Dual', 3: 'Triple'})
        # test with no family
        node = Autoland()
        node.derive(ap, td, None)
        self.assertEqual([n.index for n in node], [3, 4])
        # test with no A330
        node = Autoland()
        node.derive(ap, td, A('Family', 'A330'))
        self.assertEqual([n.index for n in node], [3, 4])
        # test with no A330
        node = Autoland()
        node.derive(ap, td, A('Family', 'B757'))
        self.assertEqual([n.index for n in node], [3])


class TestTouchAndGo(unittest.TestCase):
    def test_can_operate(self):
        expected = [('Altitude AAL', 'Go Around')]
        self.assertEqual(expected, TouchAndGo.get_operational_combinations())

    def test_derive(self):
        alt_aal = P(name='Altitude AAL', array=np.ma.array([
            5, 5, 4, 4, 3, 3, 2, 2, 1, 1,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        ]))
        go_around = [KeyTimeInstance(index=10, name='Go Around')]
        t_a_g = TouchAndGo()
        t_a_g.derive(alt_aal, go_around)
        expected = [KeyTimeInstance(index=10, name='Touch And Go')]
        self.assertEqual(t_a_g, expected)


class TestTransmit(unittest.TestCase):
    def test_can_operate(self):
        # Due to the huge number of optional dependencies, the powerset
        # generated by get_operational_combinations contains 8388608
        # combinations and raises a MemoryError.
        self.assertTrue(Transmit.can_operate(('Key HF',)))
        self.assertTrue(Transmit.can_operate(('Key HF (1)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (2)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (3)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (1) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (2) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (3) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (1) (FO)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (2) (FO)',)))
        self.assertTrue(Transmit.can_operate(('Key HF (3) (FO)',)))
        self.assertTrue(Transmit.can_operate(('Key Satcom',)))
        self.assertTrue(Transmit.can_operate(('Key Satcom (1)',)))
        self.assertTrue(Transmit.can_operate(('Key Satcom (2)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (1)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (2)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (3)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (1) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (2) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (3) (Capt)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (1) (FO)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (2) (FO)',)))
        self.assertTrue(Transmit.can_operate(('Key VHF (3) (FO)',)))

    def test_derive(self):
        hf = M('Key HF', ['Off', 'Off', 'Off', 'Keyed', 'Off', 'Off', 'Off'],
               values_mapping={0: 'Off', 1: 'Keyed'})
        tr = Transmit()
        tr.derive(hf, *[None] * 22)
        expected = [KeyTimeInstance(index=2.5, name='Transmit')]
        self.assertEqual(tr, expected)


class TestVNAVModeAndEngThrustModeRequired(unittest.TestCase, NodeTest):

    def setUp(self):
        self.node_class = VNAVModeAndEngThrustModeRequired
        self.operational_combinations = [('VNAV Mode', 'Eng Thrust Mode Required')]
    
    def test_derive_basic(self):
        vnav_mode = M(
            name='VNAV Mode',
            array=np.ma.array([1, 0, 1, 0, 1, 1, 0]),
            values_mapping={0: '-', 1: 'Engaged'},
        )
        thrust = M(
            name='Eng Thrust Mode Required',
            array=np.ma.array([0, 0, 1, 1, 1, 1, 0]),
            values_mapping={0: '-', 1: 'Required'},
        )
        node = self.node_class()
        node.derive(vnav_mode, thrust)
        self.assertEqual(node, [
            KeyTimeInstance(index=2, name='VNAV Mode And Eng Thrust Mode Required'),
            KeyTimeInstance(index=4, name='VNAV Mode And Eng Thrust Mode Required'),
        ])

class TestOffBlocks(unittest.TestCase):
    def test_can_operate(self):
        combinations = OffBlocks.get_operational_combinations()
        self.assertTrue(('Mobile',) in combinations)
        
    def test_basic(self):
        mobile = buildsections('Mobile', [5,10], [15,None])
        off = OffBlocks()
        off.get_derived((mobile,))
        self.assertEqual(len(off),1)
        self.assertEqual(off[0].index, 5)
        
    def test_none_start(self):
        mobile = buildsections('Mobile', [None,10])
        off = OffBlocks()
        off.get_derived((mobile,))
        self.assertEqual(off[0].index, 0)
        
class TestOnBlocks(unittest.TestCase):
    def test_can_operate(self):
        combinations = OnBlocks.get_operational_combinations()
        self.assertTrue(('Mobile', 'Heading') in combinations)
        
    def test_basic(self):
        mobile = buildsections('Mobile', [5, None])
        hdg = P('Heading', array=np.ma.arange(0,360,10))
        on = OnBlocks()
        on.get_derived((mobile, hdg))
        self.assertEqual(len(on),1)
        self.assertEqual(on[0].index, 36)
        
