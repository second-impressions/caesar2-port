#include <unity/unity.h>

#include "c2_port_mouse.h"

static struct c2_port_mouse mouse_state;

void setUp(void)
{
    TEST_ASSERT_TRUE(c2_port_mouse_init(&mouse_state, 640, 480, 8));
}

void tearDown(void)
{
}

static void test_initial_position_is_centered(void)
{
    TEST_ASSERT_EQUAL_INT(320, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(240, mouse_state.y);
    TEST_ASSERT_TRUE(mouse_state.inside);
}

static void test_windowed_edge_zone_maps_to_legacy_limits(void)
{
    c2_port_mouse_set_absolute(&mouse_state, 7.0f, 472.0f);
    TEST_ASSERT_EQUAL_INT(0, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(480, mouse_state.y);

    c2_port_mouse_set_absolute(&mouse_state, 8.0f, 471.0f);
    TEST_ASSERT_EQUAL_INT(8, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(471, mouse_state.y);
}

static void test_leaving_window_cancels_stale_edge_position(void)
{
    c2_port_mouse_set_absolute(&mouse_state, 0.0f, 0.0f);
    c2_port_mouse_leave(&mouse_state);
    TEST_ASSERT_EQUAL_INT(1, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(1, mouse_state.y);
    TEST_ASSERT_FALSE(mouse_state.inside);
}

static void test_active_legacy_resolution_scales_absolute_input(void)
{
    TEST_ASSERT_TRUE(c2_port_mouse_set_bounds(&mouse_state, 0, 0, 320, 200));
    c2_port_mouse_set_absolute(&mouse_state, 320.0f, 240.0f);
    TEST_ASSERT_EQUAL_INT(160, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(100, mouse_state.y);
}

static void test_relative_input_drives_a_clamped_virtual_cursor(void)
{
    c2_port_mouse_add_relative(&mouse_state, 400.0f, -300.0f);
    TEST_ASSERT_EQUAL_INT(640, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(0, mouse_state.y);
    c2_port_mouse_add_relative(&mouse_state, -1.0f, 1.0f);
    TEST_ASSERT_EQUAL_INT(639, mouse_state.x);
    TEST_ASSERT_EQUAL_INT(1, mouse_state.y);
}

static void test_engine_position_round_trips_to_frame_coordinates(void)
{
    float frame_x;
    float frame_y;

    TEST_ASSERT_TRUE(c2_port_mouse_set_bounds(&mouse_state, 0, 0, 320, 200));
    c2_port_mouse_set_position(&mouse_state, 160, 100);
    c2_port_mouse_get_frame_position(&mouse_state, &frame_x, &frame_y);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 320.0f, frame_x);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 240.0f, frame_y);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_initial_position_is_centered);
    RUN_TEST(test_windowed_edge_zone_maps_to_legacy_limits);
    RUN_TEST(test_leaving_window_cancels_stale_edge_position);
    RUN_TEST(test_active_legacy_resolution_scales_absolute_input);
    RUN_TEST(test_relative_input_drives_a_clamped_virtual_cursor);
    RUN_TEST(test_engine_position_round_trips_to_frame_coordinates);
    return UNITY_END();
}
