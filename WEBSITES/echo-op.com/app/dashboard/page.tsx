'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Users, Shield, Activity, Settings, LogOut,
  ChevronRight, Clock, Eye, UserPlus, Search, ChevronDown,
  ChevronUp, ExternalLink, Ban, Crown, Star, AlertTriangle,
  Zap, Globe, Server, Cpu, Brain, Lock,
} from 'lucide-react'
import { onAuthChange, signOut, AUTHORITY_LEVELS } from '@/lib/firebase'
import { SettingsPanel } from '@/components/settings-panel'
import type { EchoUser } from '@/lib/firebase'
import {
  collection, getDocs, query, orderBy, doc, updateDoc, deleteDoc,
  where, getDoc, Timestamp,
} from 'firebase/firestore'
import { getFirestore } from 'firebase/firestore'
import { initializeApp, getApps } from 'firebase/app'

// ═══ TYPES ═══
interface HumanRecord {
  uid: string
  email: string | null
  displayName: string | null
  photoURL: string | null
  phoneNumber: string | null
  trustLevel: number
  authority: string
  provider: string
  lastLogin: string
  updatedAt?: string
  createdAt?: string
  notes?: string
  tags?: string[]
  banned?: boolean
}

type DashTab = 'overview' | 'humans' | 'prometheus' | 'systems' | 'security' | 'settings'

// ═══ PROMETHEUS ENDPOINT REGISTRY ═══
const PROMETHEUS_CATEGORIES: {
  id: string; name: string; icon: string; color: string;
  endpoints: { id: string; path: string; label: string; method?: string }[]
}[] = [
  {
    id: 'osint', name: 'OSINT', icon: '🔍', color: 'emerald',
    endpoints: [
      { id: 'holehe', path: '/osint/holehe', label: 'Holehe Email Lookup' },
      { id: 'sherlock', path: '/osint/sherlock', label: 'Sherlock Username' },
      { id: 'maigret', path: '/osint/maigret', label: 'Maigret Deep Search' },
      { id: 'socialscan', path: '/osint/socialscan', label: 'SocialScan' },
      { id: 'phoneinfoga', path: '/osint/phoneinfoga', label: 'PhoneInfoga' },
      { id: 'whatsmyname', path: '/osint/whatsmyname', label: 'WhatsMyName' },
      { id: 'ghunt', path: '/osint/ghunt', label: 'GHunt Google' },
      { id: 'blackbird', path: '/osint/blackbird', label: 'Blackbird' },
      { id: 'mosint', path: '/osint/mosint', label: 'MOSINT' },
      { id: 'email_hunter', path: '/osint/email-hunter', label: 'Email Hunter' },
      { id: 'intelx', path: '/osint/intelx', label: 'Intelligence X' },
      { id: 'dehashed', path: '/osint/dehashed', label: 'DeHashed' },
      { id: 'spiderfoot', path: '/osint/spiderfoot', label: 'SpiderFoot' },
      { id: 'theHarvester', path: '/osint/theharvester', label: 'theHarvester' },
      { id: 'amass', path: '/osint/amass', label: 'Amass' },
      { id: 'subfinder', path: '/osint/subfinder', label: 'SubFinder' },
      { id: 'dnsdumpster', path: '/osint/dnsdumpster', label: 'DNSDumpster' },
      { id: 'whois', path: '/osint/whois', label: 'WHOIS Lookup' },
    ],
  },
  {
    id: 'network', name: 'Network', icon: '🌐', color: 'cyan',
    endpoints: [
      { id: 'nmap', path: '/network/nmap', label: 'Nmap Scan' },
      { id: 'masscan', path: '/network/masscan', label: 'Masscan' },
      { id: 'rustscan', path: '/network/rustscan', label: 'RustScan' },
      { id: 'arp_scan', path: '/network/arp-scan', label: 'ARP Scan' },
      { id: 'netdiscover', path: '/network/netdiscover', label: 'NetDiscover' },
      { id: 'traceroute', path: '/network/traceroute', label: 'Traceroute' },
      { id: 'dns_enum', path: '/network/dns-enum', label: 'DNS Enum' },
      { id: 'fierce', path: '/network/fierce', label: 'Fierce' },
      { id: 'stealth_scan', path: '/network/stealth-scan', label: 'Stealth Scan' },
      { id: 'syn_scan', path: '/network/syn-scan', label: 'SYN Scan' },
      { id: 'udp_scan', path: '/network/udp-scan', label: 'UDP Scan' },
      { id: 'os_detect', path: '/network/os-detect', label: 'OS Detection' },
      { id: 'service_detect', path: '/network/service-detect', label: 'Service Detection' },
      { id: 'vuln_scan', path: '/network/vuln-scan', label: 'Vuln Scan' },
      { id: 'ssl_scan', path: '/network/ssl-scan', label: 'SSL Scan' },
      { id: 'testssl', path: '/network/testssl', label: 'TestSSL' },
    ],
  },
  {
    id: 'exploit', name: 'Exploitation', icon: '💀', color: 'red',
    endpoints: [
      { id: 'searchsploit', path: '/exploit/searchsploit', label: 'SearchSploit' },
      { id: 'metasploit_search', path: '/exploit/metasploit/search', label: 'Metasploit Search' },
      { id: 'metasploit_run', path: '/exploit/metasploit/run', label: 'Metasploit Run', method: 'POST' },
      { id: 'nuclei', path: '/exploit/nuclei', label: 'Nuclei Scanner' },
      { id: 'nikto', path: '/exploit/nikto', label: 'Nikto' },
      { id: 'wpscan', path: '/exploit/wpscan', label: 'WPScan' },
      { id: 'sqlmap', path: '/exploit/sqlmap', label: 'SQLMap' },
      { id: 'xsser', path: '/exploit/xsser', label: 'XSSer' },
      { id: 'commix', path: '/exploit/commix', label: 'Commix' },
      { id: 'cve_search', path: '/exploit/cve-search', label: 'CVE Search' },
    ],
  },
  {
    id: 'crack', name: 'Cracking', icon: '🔑', color: 'yellow',
    endpoints: [
      { id: 'hashcat', path: '/crack/hashcat', label: 'Hashcat' },
      { id: 'john', path: '/crack/john', label: 'John the Ripper' },
      { id: 'hash_identify', path: '/crack/hash-identify', label: 'Hash Identify' },
      { id: 'hydra', path: '/crack/hydra', label: 'Hydra' },
      { id: 'medusa', path: '/crack/medusa', label: 'Medusa' },
      { id: 'ssh_brute', path: '/crack/ssh-brute', label: 'SSH Brute' },
      { id: 'ftp_brute', path: '/crack/ftp-brute', label: 'FTP Brute' },
      { id: 'rdp_brute', path: '/crack/rdp-brute', label: 'RDP Brute' },
      { id: 'smb_brute', path: '/crack/smb-brute', label: 'SMB Brute' },
      { id: 'wifi_crack', path: '/crack/wifi', label: 'WiFi Crack' },
      { id: 'wpa_crack', path: '/crack/wpa', label: 'WPA Crack' },
    ],
  },
  {
    id: 'mitm', name: 'MITM', icon: '🕵️', color: 'purple',
    endpoints: [
      { id: 'bettercap', path: '/mitm/bettercap', label: 'Bettercap' },
      { id: 'mitmproxy', path: '/mitm/mitmproxy', label: 'mitmproxy' },
      { id: 'arp_spoof', path: '/mitm/arp-spoof', label: 'ARP Spoof' },
      { id: 'dns_spoof', path: '/mitm/dns-spoof', label: 'DNS Spoof' },
      { id: 'ssl_strip', path: '/mitm/sslstrip', label: 'SSL Strip' },
      { id: 'responder', path: '/mitm/responder', label: 'Responder' },
      { id: 'ettercap', path: '/mitm/ettercap', label: 'Ettercap' },
      { id: 'evilginx', path: '/mitm/evilginx', label: 'Evilginx' },
      { id: 'gophish', path: '/mitm/gophish', label: 'GoPhish' },
    ],
  },
  {
    id: 'sigint', name: 'SIGINT', icon: '📡', color: 'orange',
    endpoints: [
      { id: 'wifi_scan', path: '/sigint/wifi-scan', label: 'WiFi Scan' },
      { id: 'wifi_deauth', path: '/sigint/wifi-deauth', label: 'WiFi Deauth' },
      { id: 'wifi_capture', path: '/sigint/wifi-capture', label: 'WiFi Capture' },
      { id: 'bluetooth_scan', path: '/sigint/bluetooth-scan', label: 'Bluetooth Scan' },
      { id: 'sdr_scan', path: '/sigint/sdr-scan', label: 'SDR Scan' },
      { id: 'rf_analyze', path: '/sigint/rf-analyze', label: 'RF Analyze' },
    ],
  },
  {
    id: 'mobile', name: 'Mobile / Android', icon: '📱', color: 'lime',
    endpoints: [
      { id: 'adb_connect', path: '/mobile/adb/connect', label: 'ADB Connect' },
      { id: 'adb_shell', path: '/mobile/adb/shell', label: 'ADB Shell' },
      { id: 'adb_devices', path: '/mobile/adb/devices', label: 'ADB Devices' },
      { id: 'adb_install', path: '/mobile/adb/install', label: 'ADB Install' },
      { id: 'adb_logcat', path: '/mobile/adb/logcat', label: 'ADB Logcat' },
      { id: 'frida_inject', path: '/mobile/frida/inject', label: 'Frida Inject' },
      { id: 'frida_spawn', path: '/mobile/frida/spawn', label: 'Frida Spawn' },
      { id: 'objection_explore', path: '/mobile/objection/explore', label: 'Objection Explore' },
      { id: 'mobsf_analyze', path: '/mobile/mobsf/analyze', label: 'MobSF Analyze' },
      { id: 'jadx_decompile', path: '/mobile/jadx/decompile', label: 'JADX Decompile' },
      { id: 'apktool_decompile', path: '/mobile/apktool/decompile', label: 'APKTool Decompile' },
      { id: 'drozer_scan', path: '/mobile/drozer/scan', label: 'Drozer Scan' },
    ],
  },
  {
    id: 'ios', name: 'iOS', icon: '🍎', color: 'sky',
    endpoints: [
      { id: 'idevice_info', path: '/ios/idevice/info', label: 'iDevice Info' },
      { id: 'idevice_pair', path: '/ios/idevice/pair', label: 'iDevice Pair' },
      { id: 'idevice_syslog', path: '/ios/idevice/syslog', label: 'iDevice Syslog' },
      { id: 'idevice_screenshot', path: '/ios/idevice/screenshot', label: 'iDevice Screenshot' },
      { id: 'idevice_apps_list', path: '/ios/idevice/apps/list', label: 'List Apps' },
      { id: 'idevice_backup', path: '/ios/idevice/backup', label: 'iDevice Backup' },
      { id: 'ifuse_mount', path: '/ios/ifuse/mount', label: 'iFuse Mount' },
      { id: 'checkra1n', path: '/ios/jailbreak/checkra1n', label: 'checkra1n JB' },
      { id: 'frida_ios_inject', path: '/ios/frida/inject', label: 'Frida iOS Inject' },
      { id: 'frida_ios_ssl_bypass', path: '/ios/frida/ssl-bypass', label: 'SSL Bypass' },
      { id: 'keychain_dump', path: '/ios/forensics/keychain', label: 'Keychain Dump' },
      { id: 'ipa_decrypt', path: '/ios/analysis/ipa-decrypt', label: 'IPA Decrypt' },
      { id: 'ssh_connect', path: '/ios/ssh/connect', label: 'SSH Connect' },
    ],
  },
  {
    id: 'frp', name: 'FRP Bypass', icon: '🔓', color: 'rose',
    endpoints: [
      { id: 'samsung_frp_adb', path: '/frp/samsung/adb', label: 'Samsung FRP ADB' },
      { id: 'samsung_frp_odin', path: '/frp/samsung/odin', label: 'Samsung FRP Odin' },
      { id: 'samsung_frp_talkback', path: '/frp/samsung/talkback', label: 'Samsung TalkBack' },
      { id: 'samsung_knox', path: '/frp/samsung/knox-bypass', label: 'Knox Bypass' },
      { id: 'google_frp_adb', path: '/frp/google/adb', label: 'Google FRP ADB' },
      { id: 'pixel_frp', path: '/frp/pixel/bypass', label: 'Pixel FRP' },
      { id: 'xiaomi_frp', path: '/frp/xiaomi/bypass', label: 'Xiaomi FRP' },
      { id: 'mdm_bypass', path: '/frp/mdm/generic', label: 'MDM Bypass' },
      { id: 'icloud_bypass', path: '/frp/apple/icloud', label: 'iCloud Bypass' },
      { id: 'screen_lock_adb', path: '/frp/screen-lock/adb', label: 'Screen Lock ADB' },
      { id: 'pin_brute', path: '/frp/screen-lock/pin-brute', label: 'PIN Brute Force' },
    ],
  },
  {
    id: 'redteam', name: 'Red Team', icon: '🔴', color: 'red',
    endpoints: [
      { id: 'cobalt_beacon', path: '/redteam/cobalt/beacon', label: 'Cobalt Beacon' },
      { id: 'empire_agent', path: '/redteam/empire/agent', label: 'Empire Agent' },
      { id: 'sliver_c2', path: '/redteam/sliver/c2', label: 'Sliver C2' },
      { id: 'bloodhound', path: '/redteam/bloodhound/collect', label: 'BloodHound Collect' },
      { id: 'mimikatz', path: '/redteam/mimikatz', label: 'Mimikatz' },
      { id: 'rubeus', path: '/redteam/rubeus', label: 'Rubeus' },
      { id: 'kerberoast', path: '/redteam/kerberoast', label: 'Kerberoast' },
      { id: 'impacket', path: '/redteam/impacket', label: 'Impacket' },
      { id: 'crackmapexec', path: '/redteam/crackmapexec', label: 'CrackMapExec' },
      { id: 'evil_winrm', path: '/redteam/evil-winrm', label: 'Evil-WinRM' },
      { id: 'dcsync', path: '/redteam/dcsync', label: 'DCSync' },
      { id: 'golden_ticket', path: '/redteam/golden-ticket', label: 'Golden Ticket' },
      { id: 'pass_the_hash', path: '/redteam/pass-the-hash', label: 'Pass the Hash' },
    ],
  },
  {
    id: 'blueteam', name: 'Blue Team', icon: '🔵', color: 'blue',
    endpoints: [
      { id: 'yara_scan', path: '/blueteam/yara/scan', label: 'YARA Scan' },
      { id: 'sigma_detect', path: '/blueteam/sigma/detect', label: 'Sigma Detect' },
      { id: 'suricata', path: '/blueteam/suricata/rules', label: 'Suricata Rules' },
      { id: 'zeek', path: '/blueteam/zeek/analyze', label: 'Zeek Analyze' },
      { id: 'volatility', path: '/blueteam/volatility/analyze', label: 'Volatility' },
      { id: 'autopsy', path: '/blueteam/autopsy/case', label: 'Autopsy Case' },
      { id: 'foremost', path: '/blueteam/foremost', label: 'Foremost' },
      { id: 'binwalk', path: '/blueteam/binwalk/analyze', label: 'Binwalk' },
      { id: 'ioc_check', path: '/blueteam/ioc-check', label: 'IOC Check' },
      { id: 'malware_analyze', path: '/blueteam/malware-analyze', label: 'Malware Analyze' },
    ],
  },
  {
    id: 'web', name: 'Web Security', icon: '🌍', color: 'indigo',
    endpoints: [
      { id: 'burp', path: '/web/burp/scan', label: 'Burp Scan' },
      { id: 'zap', path: '/web/zap/scan', label: 'ZAP Scan' },
      { id: 'wfuzz', path: '/web/wfuzz', label: 'WFuzz' },
      { id: 'ffuf', path: '/web/ffuf', label: 'FFUF' },
      { id: 'gobuster', path: '/web/gobuster', label: 'GoBuster' },
      { id: 'dirsearch', path: '/web/dirsearch', label: 'DirSearch' },
      { id: 'feroxbuster', path: '/web/feroxbuster', label: 'FeroxBuster' },
      { id: 'xss_hunter', path: '/web/xss-hunter', label: 'XSS Hunter' },
      { id: 'dalfox', path: '/web/dalfox', label: 'DalFox' },
      { id: 'sqlmap_scan', path: '/web/sqlmap', label: 'SQLMap' },
      { id: 'ssrf_detect', path: '/web/ssrf-detect', label: 'SSRF Detect' },
      { id: 'cors_check', path: '/web/cors-check', label: 'CORS Check' },
    ],
  },
  {
    id: 'cloud', name: 'Cloud Security', icon: '☁️', color: 'teal',
    endpoints: [
      { id: 'aws_enum', path: '/cloud/aws/enum', label: 'AWS Enum' },
      { id: 'aws_s3', path: '/cloud/aws/s3-scan', label: 'S3 Bucket Scan' },
      { id: 'azure_enum', path: '/cloud/azure/enum', label: 'Azure Enum' },
      { id: 'gcp_enum', path: '/cloud/gcp/enum', label: 'GCP Enum' },
      { id: 'pacu', path: '/cloud/aws/pacu', label: 'Pacu' },
      { id: 'prowler', path: '/cloud/aws/prowler', label: 'Prowler' },
      { id: 'trufflehog', path: '/cloud/trufflehog', label: 'TruffleHog' },
      { id: 'gitleaks', path: '/cloud/gitleaks', label: 'GitLeaks' },
    ],
  },
  {
    id: 'opsec', name: 'OPSEC', icon: '🛡️', color: 'violet',
    endpoints: [
      { id: 'status', path: '/opsec/status', label: 'OPSEC Status' },
      { id: 'vpn_connect', path: '/opsec/vpn/connect', label: 'VPN Connect', method: 'POST' },
      { id: 'vpn_disconnect', path: '/opsec/vpn/disconnect', label: 'VPN Disconnect', method: 'POST' },
      { id: 'vpn_status', path: '/opsec/vpn/status', label: 'VPN Status' },
      { id: 'tor_start', path: '/opsec/tor/start', label: 'Start Tor', method: 'POST' },
      { id: 'tor_stop', path: '/opsec/tor/stop', label: 'Stop Tor', method: 'POST' },
      { id: 'mac_spoof', path: '/opsec/mac/spoof', label: 'MAC Spoof', method: 'POST' },
      { id: 'mac_restore', path: '/opsec/mac/restore', label: 'MAC Restore', method: 'POST' },
      { id: 'clean_traces', path: '/opsec/clean-traces', label: 'Clean Traces', method: 'POST' },
    ],
  },
  {
    id: 'reversing', name: 'Reverse Engineering', icon: '🔬', color: 'fuchsia',
    endpoints: [
      { id: 'ghidra', path: '/reversing/ghidra/analyze', label: 'Ghidra Analyze' },
      { id: 'radare2', path: '/reversing/radare2/analyze', label: 'Radare2' },
      { id: 'binwalk_extract', path: '/reversing/binwalk/extract', label: 'Binwalk Extract' },
      { id: 'strings', path: '/reversing/strings', label: 'Strings Extract' },
      { id: 'strace', path: '/reversing/strace', label: 'strace' },
      { id: 'ltrace', path: '/reversing/ltrace', label: 'ltrace' },
      { id: 'gdb', path: '/reversing/gdb', label: 'GDB Debug' },
    ],
  },
  // ═══ NEW: Shield Protocol (Cloud Worker) ═══
  {
    id: 'shield', name: 'Shield Protocol', icon: '🛡️', color: 'amber',
    endpoints: [
      { id: 'shield_status', path: '/shield/status', label: 'Shield Status' },
      { id: 'shield_member', path: '/shield/member', label: 'Add Shield Member', method: 'POST' },
      { id: 'shield_verify', path: '/shield/verify', label: 'Verify Protection' },
      { id: 'threat_detect', path: '/threat/detect', label: 'Detect Threat', method: 'POST' },
      { id: 'threat_neutralize', path: '/threat/neutralize', label: 'Neutralize Threat', method: 'POST' },
      { id: 'threats_active', path: '/threats/active', label: 'Active Threats' },
      { id: 'threats_history', path: '/threats/history', label: 'Threat History' },
      { id: 'prom_health', path: '/health', label: 'System Health' },
      { id: 'prom_status', path: '/status', label: 'Status Summary' },
      { id: 'prom_audit', path: '/audit', label: 'Audit Trail' },
      { id: 'prom_metrics', path: '/metrics', label: 'Metrics' },
    ],
  },
  // ═══ NEW: AI Threat Analysis ═══
  {
    id: 'ai_threat', name: 'AI Threat Analysis', icon: '🧠', color: 'pink',
    endpoints: [
      { id: 'ai_analyze', path: '/analyze/event', label: 'Analyze Event', method: 'POST' },
      { id: 'ai_bulk', path: '/bulk', label: 'Bulk Analysis', method: 'POST' },
      { id: 'mitre_tactics', path: '/mitre/tactics', label: 'MITRE Tactics' },
      { id: 'mitre_techniques', path: '/mitre/techniques', label: 'MITRE Techniques' },
      { id: 'ai_configure', path: '/configure', label: 'Configure AI Provider', method: 'POST' },
      { id: 'ai_chat', path: '/chat', label: 'Chat with Prometheus', method: 'POST' },
      { id: 'ai_personalities', path: '/personalities', label: 'AI Personalities' },
    ],
  },
  // ═══ NEW: Active Directory ═══
  {
    id: 'ad_monitor', name: 'Active Directory', icon: '🏢', color: 'slate',
    endpoints: [
      { id: 'ad_alerts', path: '/ad/alerts', label: 'AD Alerts' },
      { id: 'ad_baseline', path: '/ad/baseline/capture', label: 'Capture Baseline', method: 'POST' },
      { id: 'ad_drift', path: '/ad/drift/check', label: 'Drift Check', method: 'POST' },
      { id: 'ad_drift_report', path: '/ad/drift', label: 'Drift Report' },
      { id: 'ad_ack_alert', path: '/ad/alerts/acknowledge', label: 'Acknowledge Alert', method: 'POST' },
      { id: 'ad_health', path: '/ad/health', label: 'AD Monitor Health' },
    ],
  },
  // ═══ NEW: Alert & Notification Gateway ═══
  {
    id: 'alerts', name: 'Alert Gateway', icon: '🔔', color: 'orange',
    endpoints: [
      { id: 'alert_send', path: '/alert/send', label: 'Send Alert', method: 'POST' },
      { id: 'alert_test', path: '/alert/test', label: 'Test Channel', method: 'POST' },
      { id: 'alert_monitor_start', path: '/alert/monitoring/start', label: 'Start Monitoring', method: 'POST' },
      { id: 'alert_monitor_stop', path: '/alert/monitoring/stop', label: 'Stop Monitoring', method: 'POST' },
      { id: 'alert_slack', path: '/alert/slack', label: 'Alert to Slack', method: 'POST' },
      { id: 'alert_discord', path: '/alert/discord', label: 'Alert to Discord', method: 'POST' },
      { id: 'alert_sms', path: '/alert/sms', label: 'Alert via SMS', method: 'POST' },
      { id: 'alert_email', path: '/alert/email', label: 'Alert via Email', method: 'POST' },
    ],
  },
  // ═══ NEW: Dark Web Intelligence ═══
  {
    id: 'darkweb', name: 'Dark Web Intel', icon: '🕸️', color: 'gray',
    endpoints: [
      { id: 'dw_search', path: '/darkweb/search', label: 'Search Dark Web', method: 'POST' },
      { id: 'dw_threats', path: '/darkweb/threats', label: 'Dark Web Threats' },
      { id: 'dw_monitor', path: '/darkweb/monitor/start', label: 'Brand Monitoring', method: 'POST' },
      { id: 'dw_leaks', path: '/darkweb/leaks', label: 'Data Leak Check', method: 'POST' },
      { id: 'dw_forums', path: '/darkweb/forums', label: 'Forum Intel' },
      { id: 'dw_markets', path: '/darkweb/markets', label: 'Market Intel' },
    ],
  },
  // ═══ NEW: Spyware Defense ═══
  {
    id: 'spyware', name: 'Spyware Defense', icon: '🔮', color: 'rose',
    endpoints: [
      { id: 'spy_scan', path: '/spyware/scan', label: 'Full Spyware Scan', method: 'POST' },
      { id: 'spy_pegasus', path: '/spyware/pegasus/detect', label: 'Pegasus Detection', method: 'POST' },
      { id: 'spy_ioc_check', path: '/spyware/ioc/check', label: 'IOC Check', method: 'POST' },
      { id: 'spy_yara', path: '/spyware/yara/scan', label: 'YARA Rule Scan', method: 'POST' },
      { id: 'spy_network', path: '/spyware/network/analyze', label: 'Network Analysis', method: 'POST' },
      { id: 'spy_forensics', path: '/spyware/forensics/capture', label: 'Forensic Capture', method: 'POST' },
      { id: 'spy_status', path: '/spyware/status', label: 'Defense Status' },
    ],
  },
  // ═══ NEW: Container & Kubernetes ═══
  {
    id: 'container', name: 'Container Security', icon: '🐳', color: 'cyan',
    endpoints: [
      { id: 'cont_alerts', path: '/container/alerts', label: 'Container Alerts' },
      { id: 'cont_scan', path: '/container/scan', label: 'Scan Container', method: 'POST' },
      { id: 'cont_compliance', path: '/container/compliance', label: 'Compliance Status' },
      { id: 'k8s_audit', path: '/container/k8s/audit', label: 'K8s Audit', method: 'POST' },
      { id: 'k8s_rbac', path: '/container/k8s/rbac', label: 'K8s RBAC Scan' },
      { id: 'trivy_scan', path: '/container/trivy/scan', label: 'Trivy Scan', method: 'POST' },
    ],
  },
  // ═══ NEW: Forensics & IR ═══
  {
    id: 'forensics', name: 'Forensics & IR', icon: '🔎', color: 'amber',
    endpoints: [
      { id: 'for_memory', path: '/forensics/memory/analyze', label: 'Memory Forensics', method: 'POST' },
      { id: 'for_disk', path: '/forensics/disk/analyze', label: 'Disk Analysis', method: 'POST' },
      { id: 'for_chainsaw', path: '/forensics/chainsaw', label: 'Chainsaw Logs', method: 'POST' },
      { id: 'for_hayabusa', path: '/forensics/hayabusa', label: 'Hayabusa Detect', method: 'POST' },
      { id: 'for_loki', path: '/forensics/loki', label: 'LOKI IOC Scan', method: 'POST' },
      { id: 'for_sleuthkit', path: '/forensics/sleuthkit', label: 'Sleuth Kit', method: 'POST' },
      { id: 'for_timeline', path: '/forensics/timeline', label: 'Event Timeline' },
      { id: 'for_evidence', path: '/forensics/evidence/collect', label: 'Collect Evidence', method: 'POST' },
    ],
  },
  // ═══ NEW: Credential Ops ═══
  {
    id: 'credentials', name: 'Credential Ops', icon: '🗝️', color: 'yellow',
    endpoints: [
      { id: 'cred_dump_ad', path: '/creds/ad/dump', label: 'AD Cred Dump', method: 'POST' },
      { id: 'cred_lazagne', path: '/creds/lazagne', label: 'LaZagne Extract', method: 'POST' },
      { id: 'cred_dpapi', path: '/creds/dpapi', label: 'DPAPI Secrets', method: 'POST' },
      { id: 'cred_chromium', path: '/creds/chromium', label: 'Browser Creds', method: 'POST' },
      { id: 'cred_snaffler', path: '/creds/snaffler', label: 'Snaffler Shares', method: 'POST' },
      { id: 'cred_certipy', path: '/creds/certipy', label: 'Certipy AD CS', method: 'POST' },
      { id: 'cred_kerbrute', path: '/creds/kerbrute', label: 'Kerbrute', method: 'POST' },
    ],
  },
  // ═══ NEW: Privilege Escalation ═══
  {
    id: 'privesc', name: 'Privilege Escalation', icon: '⬆️', color: 'lime',
    endpoints: [
      { id: 'pe_linpeas', path: '/privesc/linpeas', label: 'LinPEAS', method: 'POST' },
      { id: 'pe_winpeas', path: '/privesc/winpeas', label: 'WinPEAS', method: 'POST' },
      { id: 'pe_seatbelt', path: '/privesc/seatbelt', label: 'Seatbelt Check', method: 'POST' },
      { id: 'pe_suggest_linux', path: '/privesc/linux-suggest', label: 'Linux Exploit Suggest', method: 'POST' },
      { id: 'pe_suggest_win', path: '/privesc/win-suggest', label: 'Windows Exploit Suggest', method: 'POST' },
      { id: 'pe_gtfobins', path: '/privesc/gtfobins', label: 'GTFOBins Lookup' },
      { id: 'pe_lolbas', path: '/privesc/lolbas', label: 'LOLBAS Lookup' },
    ],
  },
  // ═══ NEW: Lateral Movement ═══
  {
    id: 'lateral', name: 'Lateral Movement', icon: '↔️', color: 'emerald',
    endpoints: [
      { id: 'lat_chisel', path: '/lateral/chisel', label: 'Chisel Tunnel', method: 'POST' },
      { id: 'lat_ligolo', path: '/lateral/ligolo', label: 'Ligolo Pivot', method: 'POST' },
      { id: 'lat_proxychains', path: '/lateral/proxychains', label: 'Proxychains', method: 'POST' },
      { id: 'lat_netexec', path: '/lateral/netexec', label: 'NetExec', method: 'POST' },
      { id: 'lat_spray', path: '/lateral/spray', label: 'Password Spray', method: 'POST' },
      { id: 'lat_psexec', path: '/lateral/psexec', label: 'PsExec', method: 'POST' },
      { id: 'lat_wmi', path: '/lateral/wmi', label: 'WMI Exec', method: 'POST' },
    ],
  },
  // ═══ NEW: Evasion & AV Bypass ═══
  {
    id: 'evasion', name: 'Evasion / AV Bypass', icon: '👻', color: 'zinc',
    endpoints: [
      { id: 'ev_scarecrow', path: '/evasion/scarecrow', label: 'ScareCrow Payload', method: 'POST' },
      { id: 'ev_donut', path: '/evasion/donut', label: 'Donut Shellcode', method: 'POST' },
      { id: 'ev_veil', path: '/evasion/veil', label: 'Veil Generate', method: 'POST' },
      { id: 'ev_freeze', path: '/evasion/freeze', label: 'Freeze Payload', method: 'POST' },
      { id: 'ev_inceptor', path: '/evasion/inceptor', label: 'Inceptor', method: 'POST' },
      { id: 'ev_threatcheck', path: '/evasion/threatcheck', label: 'ThreatCheck', method: 'POST' },
      { id: 'ev_defendercheck', path: '/evasion/defendercheck', label: 'DefenderCheck', method: 'POST' },
    ],
  },
  // ═══ NEW: C2 Frameworks ═══
  {
    id: 'c2', name: 'C2 Frameworks', icon: '🎮', color: 'red',
    endpoints: [
      { id: 'c2_sliver_start', path: '/c2/sliver/start', label: 'Start Sliver', method: 'POST' },
      { id: 'c2_sliver_agents', path: '/c2/sliver/agents', label: 'Sliver Agents' },
      { id: 'c2_havoc_start', path: '/c2/havoc/start', label: 'Start Havoc', method: 'POST' },
      { id: 'c2_havoc_agents', path: '/c2/havoc/agents', label: 'Havoc Agents' },
      { id: 'c2_mythic_start', path: '/c2/mythic/start', label: 'Start Mythic', method: 'POST' },
      { id: 'c2_mythic_agents', path: '/c2/mythic/agents', label: 'Mythic Agents' },
      { id: 'c2_covenant', path: '/c2/covenant/start', label: 'Start Covenant', method: 'POST' },
      { id: 'c2_villain', path: '/c2/villain/start', label: 'Start Villain', method: 'POST' },
    ],
  },
  // ═══ NEW: Voice Synthesis ═══
  {
    id: 'voice', name: 'Voice Synthesis', icon: '🎤', color: 'violet',
    endpoints: [
      { id: 'voice_list', path: '/voices', label: 'List Voices' },
      { id: 'voice_speak', path: '/speak', label: 'Generate Speech', method: 'POST' },
      { id: 'voice_prometheus', path: '/speak/prometheus', label: 'Prometheus Voice', method: 'POST' },
      { id: 'voice_echo', path: '/speak/echo', label: 'Echo Prime Voice', method: 'POST' },
      { id: 'voice_bree', path: '/speak/bree', label: 'Bree Voice', method: 'POST' },
      { id: 'voice_gs343', path: '/speak/gs343', label: 'GS343 Voice', method: 'POST' },
    ],
  },
  // ═══ NEW: Knowledge Arsenal ═══
  {
    id: 'knowledge', name: 'Knowledge Arsenal', icon: '📚', color: 'blue',
    endpoints: [
      { id: 'kb_search', path: '/knowledge/search', label: 'Search Knowledge', method: 'POST' },
      { id: 'kb_nist', path: '/knowledge/nist', label: 'NIST Controls (51 docs)' },
      { id: 'kb_mitre', path: '/knowledge/mitre', label: 'MITRE ATT&CK (53 docs)' },
      { id: 'kb_owasp', path: '/knowledge/owasp', label: 'OWASP (57 docs)' },
      { id: 'kb_cis', path: '/knowledge/cis', label: 'CIS Benchmarks (50 docs)' },
      { id: 'kb_guides', path: '/knowledge/guides', label: 'Methodology Guides (27)' },
    ],
  },
  // ═══ NEW: Deception & Honeypots ═══
  {
    id: 'deception', name: 'Deception / Honeypots', icon: '🍯', color: 'amber',
    endpoints: [
      { id: 'hp_create', path: '/deception/create', label: 'Deploy Honeypot', method: 'POST' },
      { id: 'hp_traps', path: '/deception/traps', label: 'Active Traps' },
      { id: 'hp_analyze', path: '/deception/analyze', label: 'Analyze Trap', method: 'POST' },
      { id: 'hp_canary', path: '/deception/canary/deploy', label: 'Deploy Canary', method: 'POST' },
      { id: 'hp_canary_list', path: '/deception/canary/list', label: 'List Canaries' },
    ],
  },
  // ═══ NEW: Email Security ═══
  {
    id: 'email_sec', name: 'Email Security', icon: '✉️', color: 'sky',
    endpoints: [
      { id: 'email_scan', path: '/email/scan', label: 'Scan Email', method: 'POST' },
      { id: 'email_threats', path: '/email/threats', label: 'Email Threats' },
      { id: 'email_block', path: '/email/block', label: 'Block Sender', method: 'POST' },
      { id: 'email_phish_sim', path: '/email/phishing/simulate', label: 'Phishing Sim', method: 'POST' },
    ],
  },
  // ═══ NEW: SIEM & Reporting ═══
  {
    id: 'siem', name: 'SIEM & Reports', icon: '📊', color: 'indigo',
    endpoints: [
      { id: 'siem_export', path: '/siem/export', label: 'Export to SIEM', method: 'POST' },
      { id: 'siem_status', path: '/siem/status', label: 'Export Status' },
      { id: 'siem_configure', path: '/siem/configure', label: 'Configure SIEM', method: 'POST' },
      { id: 'report_gen', path: '/reports/generate', label: 'Generate Report', method: 'POST' },
      { id: 'report_list', path: '/reports', label: 'List Reports' },
      { id: 'report_schedule', path: '/reports/schedule', label: 'Schedule Report', method: 'POST' },
    ],
  },
  // ═══ NEW: Wireless & RF ═══
  {
    id: 'wireless', name: 'Wireless & RF', icon: '📶', color: 'green',
    endpoints: [
      { id: 'wifi_monitor', path: '/wireless/monitor/start', label: 'Start WiFi Monitor', method: 'POST' },
      { id: 'wifi_evil_twin', path: '/wireless/evil-twin', label: 'Evil Twin AP', method: 'POST' },
      { id: 'wifi_pumpkin', path: '/wireless/pumpkin', label: 'WiFi-Pumpkin3', method: 'POST' },
      { id: 'wifi_eaphammer', path: '/wireless/eaphammer', label: 'EAP Hammer', method: 'POST' },
      { id: 'wifi_kismet', path: '/wireless/kismet', label: 'Kismet Scan' },
      { id: 'wifi_aircrack', path: '/wireless/aircrack', label: 'Aircrack-ng', method: 'POST' },
      { id: 'rf_jamming', path: '/wireless/rf/analyze', label: 'RF Analysis', method: 'POST' },
    ],
  },
  // ═══ NEW: Bug Bounty Recon ═══
  {
    id: 'bugbounty', name: 'Bug Bounty Recon', icon: '🏴‍☠️', color: 'orange',
    endpoints: [
      { id: 'bb_nuclei', path: '/recon/nuclei', label: 'Nuclei Scanner', method: 'POST' },
      { id: 'bb_katana', path: '/recon/katana', label: 'Katana Crawl', method: 'POST' },
      { id: 'bb_httpx', path: '/recon/httpx', label: 'Httpx Probe', method: 'POST' },
      { id: 'bb_subfinder', path: '/recon/subfinder', label: 'SubFinder', method: 'POST' },
      { id: 'bb_ffuf', path: '/recon/ffuf', label: 'FFUF Fuzz', method: 'POST' },
      { id: 'bb_arjun', path: '/recon/arjun', label: 'Arjun Params', method: 'POST' },
      { id: 'bb_paramspider', path: '/recon/paramspider', label: 'ParamSpider', method: 'POST' },
      { id: 'bb_gau', path: '/recon/gau', label: 'Get All URLs', method: 'POST' },
      { id: 'bb_wayback', path: '/recon/wayback', label: 'Wayback URLs', method: 'POST' },
      { id: 'bb_dalfox', path: '/recon/dalfox', label: 'DalFox XSS', method: 'POST' },
    ],
  },
  // ═══ NEW: Dashboard & Live View ═══
  {
    id: 'dashboard_live', name: 'Security Dashboard', icon: '📡', color: 'teal',
    endpoints: [
      { id: 'dash_main', path: '/dashboard', label: 'Full Dashboard' },
      { id: 'dash_attack_map', path: '/dashboard/attack-map', label: 'Attack Map' },
      { id: 'dash_timeline', path: '/dashboard/timeline', label: 'Threat Timeline' },
      { id: 'dash_kpis', path: '/dashboard/kpis', label: 'Security KPIs' },
      { id: 'dash_traffic', path: '/traffic/status', label: 'Traffic Monitor' },
      { id: 'dash_scheduled', path: '/scans/scheduled', label: 'Scheduled Scans' },
      { id: 'dash_backup', path: '/backup/verify', label: 'Verify Backups', method: 'POST' },
      { id: 'dash_recovery', path: '/backup/recover', label: 'Disaster Recovery', method: 'POST' },
    ],
  },
  // ═══ NEW: SSH & Remote Access ═══
  {
    id: 'ssh', name: 'SSH & Remote', icon: '💻', color: 'stone',
    endpoints: [
      { id: 'ssh_kali', path: '/ssh/execute', label: 'SSH Execute on Kali', method: 'POST' },
      { id: 'ssh_shell', path: '/ssh/shell', label: 'Interactive Shell', method: 'POST' },
      { id: 'ssh_upload', path: '/ssh/upload', label: 'Upload to Kali', method: 'POST' },
      { id: 'ssh_download', path: '/ssh/download', label: 'Download from Kali', method: 'POST' },
      { id: 'ssh_status', path: '/ssh/status', label: 'Connection Status' },
      { id: 'ssh_tunnel', path: '/ssh/tunnel', label: 'Create Tunnel', method: 'POST' },
    ],
  },
]

const TOTAL_ENDPOINTS = PROMETHEUS_CATEGORIES.reduce((sum, cat) => sum + cat.endpoints.length, 0)

// ═══ BADGE COLORS ═══
const BADGE_COLORS: Record<string, string> = {
  UNKNOWN: 'bg-gray-600',
  GUEST: 'bg-gray-500',
  USER: 'bg-blue-600',
  TRUSTED_USER: 'bg-emerald-600',
  INNER_CIRCLE: 'bg-purple-600',
  ADMIN: 'bg-orange-600',
  SOVEREIGN_ADMIN: 'bg-red-600',
  SUPREME: 'bg-yellow-500 text-black',
  SOVEREIGN_ARCHITECT: 'bg-gradient-to-r from-[#9900ff] to-[#ff6b35]',
}

const TRUST_COLOR = (level: number) => {
  if (level >= 11) return 'text-yellow-400'
  if (level >= 9) return 'text-red-400'
  if (level >= 7) return 'text-orange-400'
  if (level >= 5) return 'text-purple-400'
  if (level >= 3) return 'text-emerald-400'
  return 'text-gray-400'
}

// ═══ FIRESTORE HELPERS ═══
function getDb() {
  const app = getApps()[0]
  return getFirestore(app)
}

async function fetchAllUsers(): Promise<HumanRecord[]> {
  const db = getDb()
  const usersRef = collection(db, 'users')
  const q = query(usersRef, orderBy('trustLevel', 'desc'))
  const snapshot = await getDocs(q)
  return snapshot.docs.map((d) => ({ uid: d.id, ...d.data() } as HumanRecord))
}

async function updateUserTrust(uid: string, trustLevel: number) {
  const db = getDb()
  const authority = AUTHORITY_LEVELS[trustLevel] || 'UNKNOWN'
  await updateDoc(doc(db, 'users', uid), { trustLevel, authority, updatedAt: new Date().toISOString() })
}

async function banUser(uid: string, ban: boolean) {
  const db = getDb()
  await updateDoc(doc(db, 'users', uid), {
    banned: ban,
    trustLevel: ban ? 0 : 1,
    authority: ban ? 'UNKNOWN' : 'GUEST',
    updatedAt: new Date().toISOString(),
  })
}

// ═══ DASHBOARD COMPONENT ═══
export default function CommanderDashboard() {
  const router = useRouter()
  const [user, setUser] = useState<EchoUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<DashTab>('overview')

  // Human Database state
  const [humans, setHumans] = useState<HumanRecord[]>([])
  const [humansLoading, setHumansLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const [trustEdit, setTrustEdit] = useState<{ uid: string; level: number } | null>(null)

  useEffect(() => {
    const unsub = onAuthChange((echoUser) => {
      setUser(echoUser)
      setLoading(false)
      if (!echoUser) {
        router.push('/login')
      }
    })
    return unsub
  }, [router])

  // Load humans when Commander accesses that tab
  const loadHumans = useCallback(async () => {
    if (!user?.isCommander) return
    setHumansLoading(true)
    try {
      const data = await fetchAllUsers()
      setHumans(data)
    } catch (err) {
      console.error('Failed to load humans:', err)
    }
    setHumansLoading(false)
  }, [user])

  useEffect(() => {
    if (tab === 'humans' && user?.isCommander) {
      loadHumans()
    }
  }, [tab, user, loadHumans])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#9900ff] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-[#9900ff] mt-4 font-rajdhani">LOADING COMMAND CENTER...</p>
        </div>
      </div>
    )
  }

  if (!user) return null

  const isCommander = user.isCommander
  const filteredHumans = humans.filter((h) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      (h.email || '').toLowerCase().includes(q) ||
      (h.displayName || '').toLowerCase().includes(q) ||
      (h.authority || '').toLowerCase().includes(q) ||
      (h.provider || '').toLowerCase().includes(q)
    )
  })

  const handleTrustUpdate = async (uid: string, newLevel: number) => {
    await updateUserTrust(uid, newLevel)
    setTrustEdit(null)
    loadHumans()
  }

  const handleBan = async (uid: string, ban: boolean) => {
    await banUser(uid, ban)
    loadHumans()
  }

  // Stats
  const totalUsers = humans.length
  const commanderCount = humans.filter((h) => h.trustLevel >= 11).length
  const activeToday = humans.filter((h) => {
    if (!h.lastLogin) return false
    const d = new Date(h.lastLogin)
    const now = new Date()
    return d.toDateString() === now.toDateString()
  }).length
  const bannedCount = humans.filter((h) => h.banned).length

  // Prometheus state
  const [promStatus, setPromStatus] = useState<'online' | 'offline' | 'checking'>('checking')
  const [promExpandedCat, setPromExpandedCat] = useState<string | null>(null)
  const [promRunning, setPromRunning] = useState<string | null>(null)
  const [promOutput, setPromOutput] = useState<{ endpoint: string; data: any; success: boolean; ts: string } | null>(null)
  const [promTarget, setPromTarget] = useState('')
  const [promFilter, setPromFilter] = useState('')

  // Check Prometheus status
  useEffect(() => {
    if (tab !== 'prometheus' || !isCommander) return
    const check = async () => {
      try {
        const res = await fetch('/api/prometheus-prime', { signal: AbortSignal.timeout(5000) })
        const data = await res.json()
        setPromStatus(data.online ? 'online' : 'offline')
      } catch { setPromStatus('offline') }
    }
    check()
    const iv = setInterval(check, 30000)
    return () => clearInterval(iv)
  }, [tab, isCommander])

  const runPromEndpoint = async (path: string, method: string = 'POST') => {
    setPromRunning(path)
    setPromOutput(null)
    try {
      const res = await fetch('/api/prometheus-prime', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: path, method, params: promTarget ? { target: promTarget } : {} }),
      })
      const data = await res.json()
      setPromOutput({ endpoint: path, data, success: data.success, ts: new Date().toLocaleTimeString() })
    } catch (e: any) {
      setPromOutput({ endpoint: path, data: { error: e.message }, success: false, ts: new Date().toLocaleTimeString() })
    }
    setPromRunning(null)
  }

  const TABS: { id: DashTab; label: string; icon: typeof LayoutDashboard; commanderOnly?: boolean }[] = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'humans', label: 'Human Database', icon: Users, commanderOnly: true },
    { id: 'prometheus', label: 'Prometheus', icon: Zap, commanderOnly: true },
    { id: 'systems', label: 'Systems', icon: Server, commanderOnly: true },
    { id: 'security', label: 'Security', icon: Shield, commanderOnly: true },
    { id: 'settings', label: 'Settings', icon: Settings, commanderOnly: true },
  ]

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">

        {/* ═══ HEADER ═══ */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#9900ff] to-[#ff6b35] flex items-center justify-center shadow-lg shadow-[#9900ff]/20">
                <LayoutDashboard className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="font-orbitron text-2xl md:text-3xl font-bold text-white">
                  {isCommander ? "Commander's Dashboard" : 'Dashboard'}
                </h1>
                <p className="text-white/40 text-sm">
                  Welcome back, <span className="text-white/70">{user.displayName || user.email?.split('@')[0]}</span>
                  {' '}&mdash;{' '}
                  <span className={TRUST_COLOR(user.trustLevel)}>{user.authority.replace(/_/g, ' ')}</span>
                </p>
              </div>
            </div>
            {isCommander && (
              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/30">
                <Crown className="w-4 h-4 text-yellow-400" />
                <span className="text-yellow-400 text-sm font-semibold font-orbitron">SOVEREIGN MODE</span>
              </div>
            )}
          </div>
        </motion.div>

        {/* ═══ TABS ═══ */}
        <div className="flex gap-1 mb-8 overflow-x-auto pb-2">
          {TABS.filter((t) => !t.commanderOnly || isCommander).map((t) => {
            const Icon = t.icon
            const active = tab === t.id
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  active
                    ? 'bg-[#9900ff]/20 text-white border border-[#9900ff]/40'
                    : 'text-white/50 hover:text-white/80 hover:bg-white/5 border border-transparent'
                }`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            )
          })}
        </div>

        {/* ═══ OVERVIEW TAB ═══ */}
        <AnimatePresence mode="wait">
          {tab === 'overview' && (
            <motion.div key="overview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              {/* User Profile Card */}
              <div className="glass-panel p-6 mb-6">
                <div className="flex items-center gap-4">
                  {user.photoURL ? (
                    <img src={user.photoURL} alt="" className="w-16 h-16 rounded-full border-2 border-[#9900ff]/50" />
                  ) : (
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[#9900ff] to-[#ff6b35] flex items-center justify-center text-white text-2xl font-bold">
                      {(user.displayName || user.email || '?')[0].toUpperCase()}
                    </div>
                  )}
                  <div className="flex-1">
                    <h2 className="text-xl font-bold text-white">{user.displayName || 'User'}</h2>
                    <p className="text-white/40 text-sm">{user.email}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${BADGE_COLORS[user.authority] || 'bg-gray-600'} text-white`}>
                        {user.authority.replace(/_/g, ' ')}
                      </span>
                      <span className="text-white/30 text-xs">Trust Level {user.trustLevel}</span>
                      <span className="text-white/30 text-xs">via {user.provider}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Stats (Commander only) */}
              {isCommander && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  {[
                    { label: 'Total Users', value: totalUsers || '...', icon: Users, color: 'text-[#00ffff]' },
                    { label: 'Active Today', value: activeToday || '...', icon: Activity, color: 'text-emerald-400' },
                    { label: 'Commanders', value: commanderCount || '0', icon: Crown, color: 'text-yellow-400' },
                    { label: 'Banned', value: bannedCount || '0', icon: Ban, color: 'text-red-400' },
                  ].map((stat) => {
                    const Icon = stat.icon
                    return (
                      <div key={stat.label} className="glass-panel p-4">
                        <div className="flex items-center gap-2 mb-1">
                          <Icon className={`w-4 h-4 ${stat.color}`} />
                          <span className="text-white/40 text-xs">{stat.label}</span>
                        </div>
                        <p className={`text-2xl font-bold font-orbitron ${stat.color}`}>{stat.value}</p>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Quick Actions — Commander/Bloodline Only */}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  ...(isCommander ? [
                    { label: 'Prometheus Prime', desc: '206+ security endpoints on Kali', href: '#', icon: Zap, color: 'from-orange-600 to-red-600', onClick: () => setTab('prometheus') },
                    { label: 'Human Database', desc: 'Manage all users', href: '#', icon: Users, color: 'from-emerald-600 to-teal-600', onClick: () => setTab('humans') },
                    { label: 'Command Center', desc: 'Engine fleet & FORGE-X controls', href: '/command-center', icon: Brain, color: 'from-yellow-600 to-orange-600' },
                    { label: 'Security', desc: 'Auth, vault & trust levels', href: '#', icon: Shield, color: 'from-purple-600 to-indigo-600', onClick: () => setTab('security') },
                    { label: 'Systems', desc: 'Cloud infrastructure status', href: '#', icon: Server, color: 'from-cyan-600 to-blue-600', onClick: () => setTab('systems') },
                  ] : []),
                ].map((action) => {
                  const Icon = action.icon
                  const inner = (
                    <div className="glass-panel p-5 group hover:border-[#9900ff]/40 transition-all cursor-pointer">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${action.color} flex items-center justify-center`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h3 className="text-white font-semibold text-sm">{action.label}</h3>
                            <p className="text-white/40 text-xs">{action.desc}</p>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-white/50 transition-colors" />
                      </div>
                    </div>
                  )
                  if ('onClick' in action && action.onClick) {
                    return <div key={action.label} onClick={action.onClick}>{inner}</div>
                  }
                  return <Link key={action.label} href={action.href}>{inner}</Link>
                })}
              </div>

              {/* Permissions */}
              <div className="glass-panel p-6 mt-6">
                <h3 className="text-white/60 text-xs uppercase tracking-wider mb-3">Your Permissions</h3>
                <div className="flex flex-wrap gap-2">
                  {user.permissions.map((perm) => (
                    <span key={perm} className="text-xs px-2.5 py-1 rounded-full bg-white/5 text-white/60 border border-white/10">
                      {perm.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {/* ═══ HUMAN DATABASE TAB ═══ */}
          {tab === 'humans' && isCommander && (
            <motion.div key="humans" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              {/* Search + Stats Bar */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 mb-6">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                  <input
                    type="text"
                    placeholder="Search by name, email, authority, provider..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[#9900ff]/50"
                  />
                </div>
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <Users className="w-4 h-4" />
                  <span>{filteredHumans.length} of {humans.length} users</span>
                </div>
                <button
                  onClick={loadHumans}
                  className="px-4 py-2.5 bg-[#9900ff]/20 text-[#9900ff] border border-[#9900ff]/30 rounded-lg text-sm hover:bg-[#9900ff]/30 transition-colors"
                >
                  Refresh
                </button>
              </div>

              {/* User Table */}
              {humansLoading ? (
                <div className="flex items-center justify-center py-16">
                  <div className="w-8 h-8 border-2 border-[#9900ff] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Header */}
                  <div className="hidden md:grid grid-cols-12 gap-2 px-4 py-2 text-xs text-white/30 uppercase tracking-wider">
                    <div className="col-span-3">User</div>
                    <div className="col-span-2">Authority</div>
                    <div className="col-span-2">Provider</div>
                    <div className="col-span-2">Last Login</div>
                    <div className="col-span-1">Trust</div>
                    <div className="col-span-2">Actions</div>
                  </div>

                  {filteredHumans.map((h) => {
                    const isExpanded = expandedUser === h.uid
                    const isBanned = h.banned
                    const isEditingTrust = trustEdit?.uid === h.uid

                    return (
                      <div
                        key={h.uid}
                        className={`glass-panel overflow-hidden transition-all ${isBanned ? 'opacity-50 border-red-500/30' : ''}`}
                      >
                        {/* Row */}
                        <div
                          className="grid grid-cols-12 gap-2 items-center px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors"
                          onClick={() => setExpandedUser(isExpanded ? null : h.uid)}
                        >
                          {/* User */}
                          <div className="col-span-12 md:col-span-3 flex items-center gap-3">
                            {h.photoURL ? (
                              <img src={h.photoURL} alt="" className="w-8 h-8 rounded-full" />
                            ) : (
                              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#9900ff] to-[#00ffff] flex items-center justify-center text-white text-xs font-bold">
                                {(h.displayName || h.email || '?')[0].toUpperCase()}
                              </div>
                            )}
                            <div className="min-w-0">
                              <p className="text-white text-sm font-medium truncate">
                                {h.displayName || h.email?.split('@')[0] || 'Unknown'}
                                {isBanned && <Ban className="inline w-3 h-3 text-red-400 ml-1" />}
                              </p>
                              <p className="text-white/30 text-xs truncate">{h.email || h.phoneNumber || h.uid}</p>
                            </div>
                          </div>

                          {/* Authority */}
                          <div className="hidden md:block col-span-2">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${BADGE_COLORS[h.authority] || 'bg-gray-600'} text-white`}>
                              {(h.authority || 'UNKNOWN').replace(/_/g, ' ')}
                            </span>
                          </div>

                          {/* Provider */}
                          <div className="hidden md:block col-span-2">
                            <span className="text-white/50 text-xs capitalize">{h.provider || 'unknown'}</span>
                          </div>

                          {/* Last Login */}
                          <div className="hidden md:block col-span-2">
                            <span className="text-white/40 text-xs">
                              {h.lastLogin ? new Date(h.lastLogin).toLocaleDateString() : 'Never'}
                            </span>
                          </div>

                          {/* Trust */}
                          <div className="hidden md:block col-span-1">
                            <span className={`font-mono text-sm font-bold ${TRUST_COLOR(h.trustLevel)}`}>
                              {h.trustLevel}
                            </span>
                          </div>

                          {/* Actions */}
                          <div className="hidden md:flex col-span-2 items-center justify-end">
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-white/30" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-white/30" />
                            )}
                          </div>
                        </div>

                        {/* Expanded Details */}
                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="border-t border-white/5"
                            >
                              <div className="px-4 py-4 space-y-4">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                  <div>
                                    <span className="text-white/30 text-xs">UID</span>
                                    <p className="text-white/60 font-mono text-xs truncate">{h.uid}</p>
                                  </div>
                                  <div>
                                    <span className="text-white/30 text-xs">Phone</span>
                                    <p className="text-white/60 text-xs">{h.phoneNumber || 'N/A'}</p>
                                  </div>
                                  <div>
                                    <span className="text-white/30 text-xs">Last Login</span>
                                    <p className="text-white/60 text-xs">{h.lastLogin ? new Date(h.lastLogin).toLocaleString() : 'Never'}</p>
                                  </div>
                                  <div>
                                    <span className="text-white/30 text-xs">Provider</span>
                                    <p className="text-white/60 text-xs capitalize">{h.provider}</p>
                                  </div>
                                </div>

                                {/* Trust Level Editor */}
                                <div className="flex items-center gap-3">
                                  <span className="text-white/30 text-xs">Set Trust Level:</span>
                                  <div className="flex gap-1">
                                    {[0, 1, 2, 3, 5, 7, 9, 10, 11].map((lvl) => (
                                      <button
                                        key={lvl}
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          handleTrustUpdate(h.uid, lvl)
                                        }}
                                        className={`w-7 h-7 rounded text-xs font-bold transition-all ${
                                          h.trustLevel === lvl
                                            ? 'bg-[#9900ff] text-white scale-110'
                                            : 'bg-white/5 text-white/40 hover:bg-white/10 hover:text-white'
                                        }`}
                                      >
                                        {lvl}
                                      </button>
                                    ))}
                                  </div>
                                </div>

                                {/* Actions */}
                                <div className="flex gap-2">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handleBan(h.uid, !h.banned)
                                    }}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                                      h.banned
                                        ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                                        : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                                    }`}
                                  >
                                    {h.banned ? <UserPlus className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
                                    {h.banned ? 'Unban' : 'Ban User'}
                                  </button>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )
                  })}

                  {filteredHumans.length === 0 && !humansLoading && (
                    <div className="text-center py-16 text-white/30">
                      <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p>No users found</p>
                      <p className="text-xs mt-1">Users are automatically added when they sign up or log in</p>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* ═══ PROMETHEUS CONTROL ROOM ═══ */}
          {tab === 'prometheus' && isCommander && (
            <motion.div key="prometheus" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              {/* Header Bar */}
              <div className="glass-panel p-4 mb-6">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-600 to-red-600 flex items-center justify-center">
                      <Zap className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white font-orbitron">PROMETHEUS PRIME</h2>
                      <p className="text-white/40 text-xs">Full Arsenal Control Room &mdash; Kali 192.168.1.202 &bull; 120+ Tools &bull; 238 Knowledge Docs &bull; SSH Exec</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
                      promStatus === 'online' ? 'border-emerald-500/40 bg-emerald-500/10' :
                      promStatus === 'offline' ? 'border-red-500/40 bg-red-500/10' :
                      'border-yellow-500/40 bg-yellow-500/10'
                    }`}>
                      <div className={`w-2 h-2 rounded-full ${
                        promStatus === 'online' ? 'bg-emerald-400 animate-pulse' :
                        promStatus === 'offline' ? 'bg-red-400' : 'bg-yellow-400 animate-pulse'
                      }`} />
                      <span className={`text-xs font-mono ${
                        promStatus === 'online' ? 'text-emerald-400' :
                        promStatus === 'offline' ? 'text-red-400' : 'text-yellow-400'
                      }`}>{promStatus.toUpperCase()}</span>
                    </div>
                    <div className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
                      <span className="text-white/60 text-xs font-mono">{TOTAL_ENDPOINTS} Endpoints</span>
                    </div>
                    <div className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
                      <span className="text-white/60 text-xs font-mono">{PROMETHEUS_CATEGORIES.length} Categories</span>
                    </div>
                  </div>
                </div>

                {/* Target Input */}
                <div className="mt-4 flex gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                    <input
                      type="text"
                      value={promTarget}
                      onChange={(e) => setPromTarget(e.target.value)}
                      placeholder="Target (IP, domain, email, hash, etc.)"
                      className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-orange-500/50 font-mono"
                    />
                  </div>
                  <div className="relative w-72">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                    <input
                      type="text"
                      value={promFilter}
                      onChange={(e) => setPromFilter(e.target.value)}
                      placeholder="Filter categories / tools..."
                      className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-violet-500/50 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Category Grid */}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
                {PROMETHEUS_CATEGORIES.filter((cat) => {
                  if (!promFilter) return true
                  const q = promFilter.toLowerCase()
                  return cat.name.toLowerCase().includes(q) || cat.id.includes(q) || cat.endpoints.some(ep => ep.label.toLowerCase().includes(q))
                }).map((cat) => {
                  const isExpanded = promExpandedCat === cat.id
                  return (
                    <div key={cat.id} className={`glass-panel overflow-hidden transition-all ${isExpanded ? 'md:col-span-2 lg:col-span-3' : ''}`}>
                      <button
                        onClick={() => setPromExpandedCat(isExpanded ? null : cat.id)}
                        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{cat.icon}</span>
                          <div className="text-left">
                            <h3 className="text-white font-semibold text-sm">{cat.name}</h3>
                            <p className="text-white/30 text-xs">{cat.endpoints.length} tools</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-white/20 text-xs font-mono">{cat.id.toUpperCase()}</span>
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-white/30" /> : <ChevronDown className="w-4 h-4 text-white/30" />}
                        </div>
                      </button>

                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="border-t border-white/5"
                          >
                            <div className="p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                              {cat.endpoints.map((ep) => (
                                <button
                                  key={ep.id}
                                  disabled={promRunning !== null}
                                  onClick={() => runPromEndpoint(ep.path, ep.method || 'POST')}
                                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-left text-xs font-mono transition-all border ${
                                    promRunning === ep.path
                                      ? 'border-orange-500/50 bg-orange-500/10 text-orange-300'
                                      : promOutput?.endpoint === ep.path
                                        ? promOutput.success
                                          ? 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300'
                                          : 'border-red-500/30 bg-red-500/5 text-red-300'
                                        : 'border-white/10 bg-white/5 text-white/60 hover:bg-white/10 hover:text-white hover:border-orange-500/30'
                                  } disabled:opacity-50`}
                                >
                                  {promRunning === ep.path ? (
                                    <div className="w-3 h-3 border-2 border-orange-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                                  ) : (
                                    <Zap className="w-3 h-3 flex-shrink-0 opacity-50" />
                                  )}
                                  <span className="truncate">{ep.label}</span>
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  )
                })}
              </div>

              {/* Output Panel */}
              {promOutput && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`glass-panel p-4 border ${
                    promOutput.success ? 'border-emerald-500/30' : 'border-red-500/30'
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${promOutput.success ? 'bg-emerald-400' : 'bg-red-400'}`} />
                      <span className="text-white font-mono text-sm">{promOutput.endpoint}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        promOutput.success ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                      }`}>{promOutput.success ? 'SUCCESS' : 'FAILED'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-white/30 text-xs">{promOutput.ts}</span>
                      <button
                        onClick={() => setPromOutput(null)}
                        className="text-white/30 hover:text-white/60 text-xs"
                      >CLEAR</button>
                    </div>
                  </div>
                  <pre className="bg-black/50 rounded-lg p-4 text-xs text-white/70 font-mono overflow-x-auto max-h-96 overflow-y-auto">
                    {JSON.stringify(promOutput.data, null, 2)}
                  </pre>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* ═══ SYSTEMS TAB ═══ */}
          {tab === 'systems' && isCommander && (
            <motion.div key="systems" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { name: 'Cognition Cloud', status: 'online', workers: 10, url: 'https://ekm-query.bmcii1976.workers.dev', color: 'emerald' },
                  { name: 'Swarm Brain', status: 'online', workers: 1, url: 'https://echo-swarm-brain.bmcii1976.workers.dev', color: 'purple' },
                  { name: 'ShadowGlass v8', status: 'online', workers: 1, url: 'https://shadowglass-v8-warpspeed.bmcii1976.workers.dev', color: 'cyan' },
                  { name: 'Build Orchestrator', status: 'online', workers: 1, url: 'https://echo-build-orchestrator.bmcii1976.workers.dev', color: 'orange' },
                  { name: 'Omniscient Sync', status: 'online', workers: 1, url: 'https://omniscient-sync.bmcii1976.workers.dev', color: 'blue' },
                  { name: 'ENCORE Scraper', status: 'online', workers: 1, url: 'https://encore-cloud-scraper.bmcii1976.workers.dev', color: 'red' },
                ].map((sys) => (
                  <div key={sys.name} className="glass-panel p-5">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-white font-semibold text-sm">{sys.name}</h3>
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full bg-${sys.color}-400 animate-pulse`} />
                        <span className={`text-xs text-${sys.color}-400`}>{sys.status}</span>
                      </div>
                    </div>
                    <p className="text-white/30 text-xs mb-3">{sys.workers} worker{sys.workers > 1 ? 's' : ''}</p>
                    <a
                      href={sys.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-[#9900ff] hover:text-[#bb44ff] transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      View Status
                    </a>
                  </div>
                ))}
              </div>

              {/* Cloud Stats */}
              <div className="glass-panel p-6 mt-6">
                <h3 className="text-white/60 text-xs uppercase tracking-wider mb-4">Cloud Infrastructure</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'Workers', value: '26', icon: Globe },
                    { label: 'D1 Databases', value: '10', icon: Server },
                    { label: 'R2 Buckets', value: '10', icon: Cpu },
                    { label: 'KV Namespaces', value: '20', icon: Zap },
                  ].map((s) => {
                    const Icon = s.icon
                    return (
                      <div key={s.label} className="text-center">
                        <Icon className="w-5 h-5 text-[#00ffff] mx-auto mb-1" />
                        <p className="text-white font-bold font-orbitron">{s.value}</p>
                        <p className="text-white/30 text-xs">{s.label}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* ═══ SECURITY TAB ═══ */}
          {tab === 'security' && isCommander && (
            <motion.div key="security" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="space-y-4">
                <div className="glass-panel p-6">
                  <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                    <Shield className="w-5 h-5 text-[#9900ff]" />
                    Security Overview
                  </h3>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="bg-white/5 rounded-lg p-4">
                      <p className="text-white/40 text-xs mb-1">Master Vault</p>
                      <p className="text-emerald-400 font-bold">1,527 Credentials</p>
                      <p className="text-white/30 text-xs mt-1">AES-256-GCM Encrypted</p>
                    </div>
                    <div className="bg-white/5 rounded-lg p-4">
                      <p className="text-white/40 text-xs mb-1">Auth Providers</p>
                      <p className="text-[#00ffff] font-bold">5 Active</p>
                      <p className="text-white/30 text-xs mt-1">Google, Apple, Facebook, Email, Phone</p>
                    </div>
                    <div className="bg-white/5 rounded-lg p-4">
                      <p className="text-white/40 text-xs mb-1">Authority Levels</p>
                      <p className="text-yellow-400 font-bold">11 Tiers</p>
                      <p className="text-white/30 text-xs mt-1">UNKNOWN to SOVEREIGN</p>
                    </div>
                  </div>
                </div>

                <div className="glass-panel p-6">
                  <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-400" />
                    Trust Level Distribution
                  </h3>
                  <div className="space-y-2">
                    {Object.entries(AUTHORITY_LEVELS).map(([level, name]) => {
                      const lvl = parseInt(level)
                      const count = humans.filter((h) => h.trustLevel === lvl).length
                      const pct = totalUsers > 0 ? (count / totalUsers) * 100 : 0
                      if (count === 0) return null
                      return (
                        <div key={level} className="flex items-center gap-3">
                          <span className="text-white/40 text-xs w-36 truncate">{name.replace(/_/g, ' ')}</span>
                          <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-[#9900ff] to-[#00ffff] transition-all"
                              style={{ width: `${Math.max(pct, 2)}%` }}
                            />
                          </div>
                          <span className="text-white/60 text-xs font-mono w-8 text-right">{count}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* ═══ SETTINGS TAB (Commander Only) ═══ */}
          {tab === 'settings' && isCommander && (
            <motion.div key="settings" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <SettingsPanel embedded={true} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
