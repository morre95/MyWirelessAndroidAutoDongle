// SPDX-License-Identifier: MIT
// One ephemeral, owner-assisted headless pairing window; no profile authorization.
#include <gio/gio.h>
#include <glib-unix.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

#define ADAPTER "/org/bluez/hci0"
#define AGENT "/test/radxa/agent"
static GDBusConnection *bus;
static GMainLoop *loop;
static char *owner, *candidate;
static gboolean window_open;
static int outcome = 10;
static guint timer;

static GVariant *invoke(const char *path, const char *interface, const char *method,
                        GVariant *args, const GVariantType *type)
{
    GError *error = NULL;
    GVariant *reply = g_dbus_connection_call_sync(bus, owner, path, interface,
        method, args, type, G_DBUS_CALL_FLAGS_NONE, 2000, NULL, &error);
    if (!reply) {
        g_printerr("%s.%s failed: %s\n", interface, method, error->message);
        g_error_free(error);
    }
    return reply;
}

static gboolean set_property(const char *name, GVariant *value)
{
    GVariant *reply = invoke(ADAPTER, "org.freedesktop.DBus.Properties", "Set",
        g_variant_new("(ssv)", "org.bluez.Adapter1", name, value), G_VARIANT_TYPE_UNIT);
    if (!reply) return FALSE;
    g_variant_unref(reply);
    return TRUE;
}

static gboolean check_boolean(const char *path, const char *interface,
                              const char *name, gboolean expected)
{
    GVariant *reply = invoke(path, "org.freedesktop.DBus.Properties", "Get",
        g_variant_new("(ss)", interface, name), G_VARIANT_TYPE("(v)"));
    if (!reply) return FALSE;
    GVariant *value;
    g_variant_get(reply, "(v)", &value);
    gboolean valid = g_variant_is_of_type(value, G_VARIANT_TYPE_BOOLEAN) &&
                     g_variant_get_boolean(value) == expected;
    g_variant_unref(value);
    g_variant_unref(reply);
    return valid;
}

static gboolean stop(gpointer unused G_GNUC_UNUSED)
{
    outcome = 11;
    g_main_loop_quit(loop);
    return G_SOURCE_CONTINUE;
}

static gboolean expired(gpointer unused G_GNUC_UNUSED)
{
    timer = 0;
    stop(NULL);
    return G_SOURCE_REMOVE;
}

static void agent_call(GDBusConnection *connection G_GNUC_UNUSED, const char *sender,
    const char *path G_GNUC_UNUSED, const char *interface G_GNUC_UNUSED,
    const char *method, GVariant *args, GDBusMethodInvocation *request,
    gpointer unused G_GNUC_UNUSED)
{
    if (g_strcmp0(sender, owner) != 0) goto reject;
    if (!strcmp(method, "Release")) {
        g_dbus_method_invocation_return_value(request, NULL);
        stop(NULL);
        return;
    }
    if (!strcmp(method, "Cancel")) {
        g_clear_pointer(&candidate, g_free);
        g_dbus_method_invocation_return_value(request, NULL);
        return;
    }
    if (window_open && (!strcmp(method, "RequestAuthorization") ||
                        !strcmp(method, "RequestConfirmation"))) {
        const char *device;
        g_variant_get_child(args, 0, "&o", &device);
        if (!g_str_has_prefix(device, ADAPTER "/dev_") ||
            (candidate && strcmp(device, candidate))) goto reject;
        if (!candidate) candidate = g_strdup(device);
        g_dbus_method_invocation_return_value(request, NULL);
        return;
    }
reject:
    g_dbus_method_invocation_return_dbus_error(request, "org.bluez.Error.Rejected",
                                              "Outside this diagnostic pairing window");
}

static void changed(GDBusConnection *connection G_GNUC_UNUSED,
    const char *sender G_GNUC_UNUSED, const char *path,
    const char *interface G_GNUC_UNUSED, const char *signal G_GNUC_UNUSED,
    GVariant *args, gpointer unused G_GNUC_UNUSED)
{
    if (!window_open || !g_str_has_prefix(path, ADAPTER "/dev_") ||
        (candidate && strcmp(path, candidate)) ||
        !g_variant_is_of_type(args, G_VARIANT_TYPE("(sa{sv}as)"))) return;
    const char *kind;
    GVariant *values, *invalid;
    gboolean paired = FALSE;
    g_variant_get(args, "(&s@a{sv}@as)", &kind, &values, &invalid);
    if (!strcmp(kind, "org.bluez.Device1") &&
        g_variant_lookup(values, "Paired", "b", &paired) && paired) {
        outcome = check_boolean(path, "org.bluez.Device1", "Paired", TRUE) ? 0 : 12;
        g_main_loop_quit(loop);
    }
    g_variant_unref(values);
    g_variant_unref(invalid);
}

static void owner_changed(GDBusConnection *connection G_GNUC_UNUSED,
    const char *sender G_GNUC_UNUSED, const char *path G_GNUC_UNUSED,
    const char *interface G_GNUC_UNUSED, const char *signal G_GNUC_UNUSED,
    GVariant *args G_GNUC_UNUSED, gpointer unused G_GNUC_UNUSED)
{
    stop(NULL);
}

int main(int argc, char **argv)
{
    char *end = NULL;
    guint64 seconds = argc == 3 ? g_ascii_strtoull(argv[2], &end, 10) : 0;
    if (argc != 3 || !end || *end || seconds < 1 || seconds > 180) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    GError *error = NULL;
    bus = g_dbus_connection_new_for_address_sync(argv[1],
        G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT |
        G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION, NULL, NULL, &error);
    if (!bus) {
        g_printerr("D-Bus unavailable: %s\n", error->message);
        g_error_free(error);
        return 10;
    }
    g_dbus_connection_set_exit_on_close(bus, FALSE);
    GVariant *reply = g_dbus_connection_call_sync(bus, "org.freedesktop.DBus",
        "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetNameOwner",
        g_variant_new("(s)", "org.bluez"), G_VARIANT_TYPE("(s)"), 0, 2000, NULL, NULL);
    if (!reply) { g_object_unref(bus); return 10; }
    g_variant_get(reply, "(s)", &owner);
    g_variant_unref(reply);
    loop = g_main_loop_new(NULL, FALSE);
    const char xml[] = "<node><interface name='org.bluez.Agent1'>"
        "<method name='Release'/><method name='Cancel'/>"
        "<method name='RequestAuthorization'><arg type='o' direction='in'/></method>"
        "<method name='RequestConfirmation'><arg type='o' direction='in'/>"
        "<arg type='u' direction='in'/></method>"
        "<method name='AuthorizeService'><arg type='o' direction='in'/>"
        "<arg type='s' direction='in'/></method></interface></node>";
    GDBusNodeInfo *info = g_dbus_node_info_new_for_xml(xml, NULL);
    const GDBusInterfaceVTable vtable = {.method_call = agent_call};
    guint object = g_dbus_connection_register_object(bus, AGENT, info->interfaces[0],
                                                     &vtable, NULL, NULL, NULL);
    gboolean registered = FALSE;
    guint subscription = g_dbus_connection_signal_subscribe(bus, owner,
        "org.freedesktop.DBus.Properties", "PropertiesChanged", NULL, NULL, 0,
        changed, NULL, NULL);
    guint watch = g_dbus_connection_signal_subscribe(bus, "org.freedesktop.DBus",
        "org.freedesktop.DBus", "NameOwnerChanged", "/org/freedesktop/DBus",
        "org.bluez", 0, owner_changed, NULL, NULL);
    guint term = g_unix_signal_add(SIGTERM, stop, NULL);
    if (!object) goto cleanup;
    reply = invoke("/org/bluez", "org.bluez.AgentManager1", "RegisterAgent",
        g_variant_new("(os)", AGENT, "NoInputNoOutput"), G_VARIANT_TYPE_UNIT);
    if (!reply) goto cleanup;
    g_variant_unref(reply);
    registered = TRUE;
    reply = invoke("/org/bluez", "org.bluez.AgentManager1", "RequestDefaultAgent",
        g_variant_new("(o)", AGENT), G_VARIANT_TYPE_UNIT);
    if (!reply) goto cleanup;
    g_variant_unref(reply);
    if (!set_property("Powered", g_variant_new_boolean(TRUE)) ||
        !check_boolean(ADAPTER, "org.bluez.Adapter1", "Powered", TRUE)) goto cleanup;
    puts("ADAPTER_POWERED=1");
    if (!set_property("Alias", g_variant_new_string("Radxa Mainline Test")) ||
        !set_property("PairableTimeout", g_variant_new_uint32((guint32)seconds)) ||
        !set_property("DiscoverableTimeout", g_variant_new_uint32((guint32)seconds)) ||
        !set_property("Pairable", g_variant_new_boolean(TRUE)) ||
        !set_property("Discoverable", g_variant_new_boolean(TRUE))) goto cleanup;
    window_open = TRUE;
    puts("PAIRING_WINDOW_OPEN=1");
    timer = g_timeout_add((guint)seconds * 1000, expired, NULL);
    g_main_loop_run(loop);
cleanup:
    window_open = FALSE;
    if (timer) g_source_remove(timer);
    g_source_remove(term);
    gboolean clean = set_property("Discoverable", g_variant_new_boolean(FALSE));
    clean = set_property("Pairable", g_variant_new_boolean(FALSE)) && clean;
    clean = check_boolean(ADAPTER, "org.bluez.Adapter1", "Discoverable", FALSE) && clean;
    clean = check_boolean(ADAPTER, "org.bluez.Adapter1", "Pairable", FALSE) && clean;
    if (registered) {
        reply = invoke("/org/bluez", "org.bluez.AgentManager1", "UnregisterAgent",
                        g_variant_new("(o)", AGENT), G_VARIANT_TYPE_UNIT);
        if (reply) g_variant_unref(reply); else clean = FALSE;
    }
    if (!clean) outcome = 13;
    if (object) g_dbus_connection_unregister_object(bus, object);
    g_dbus_connection_signal_unsubscribe(bus, subscription);
    g_dbus_connection_signal_unsubscribe(bus, watch);
    g_dbus_node_info_unref(info);
    g_main_loop_unref(loop);
    g_dbus_connection_close_sync(bus, NULL, NULL);
    g_object_unref(bus);
    g_free(owner);
    g_free(candidate);
    puts(outcome == 0 ? "PAIRING_RESULT=success" : "PAIRING_RESULT=failed");
    return outcome;
}
