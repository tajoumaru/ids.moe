package handler

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

var (
	rdb *redis.Client
	ctx = context.Background()
)

// Platform synonyms mapping
var platformSynonyms = map[string][]string{
	"anidb":            {"ad", "adb", "anidb.net"},
	"anilist":          {"al", "anilist.co"},
	"animenewsnetwork": {"an", "ann", "animenewsnetwork.com"},
	"animeplanet":      {"ap", "anime-planet", "anime-planet.com", "animeplanet.com"},
	"anisearch":        {"as", "anisearch.de", "anisearch.es", "anisearch.fr", "anisearch.it", "anisearch.jp", "anisearch.com"},
	"annict":           {"ac", "act", "anc", "annict.com", "annict.jp", "en.annict.com"},
	"imdb":             {"im", "imdb.com"},
	"kaize":            {"kz", "kaize.io"},
	"kitsu":            {"kt", "kts", "kitsu.app", "kitsu.io"},
	"kurozora":         {"kr", "krz", "kurozora.app"},
	"letterboxd":       {"lb", "letterboxd.com"},
	"livechart":        {"lc", "livechart.me"},
	"myanili":          {"my", "myani.li"},
	"myanimelist":      {"ma", "mal", "myanimelist.net"},
	"nautiljon":        {"nj", "ntj", "nautiljon.com"},
	"notify":           {"nf", "ntf", "ntm", "notifymoe", "notify.moe"},
	"otakotaku":        {"oo", "otakotaku.com"},
	"shikimori":        {"sh", "shk", "shiki", "shikimori.me", "shikimori.one", "shikimori.org"},
	"shoboi":           {"sb", "shb", "syb", "syoboi", "shobocal", "syobocal", "cal.syoboi.jp"},
	"silveryasha":      {"sy", "dbti", "db.silveryasha.id", "db.silveryasha.web.id"},
	"simkl":            {"sm", "smk", "simkl.com", "animecountdown", "animecountdown.com"},
	"themoviedb":       {"tm", "tmdb", "tmdb.org"},
	"trakt":            {"tr", "trk", "trakt.tv"},
}

// Route paths for building URIs
var routePaths = map[string]string{
	"anidb":            "https://anidb.net/anime/",
	"anilist":          "https://anilist.co/anime/",
	"animenewsnetwork": "https://animenewsnetwork/encyclopedia/anime?id=",
	"animeplanet":      "https://www.anime-planet.com/anime/",
	"anisearch":        "https://www.anisearch.com/anime/",
	"annict":           "https://annict.com/works/",
	"imdb":             "https://www.imdb.com/title/",
	"kaize":            "https://kaize.io/anime/",
	"kitsu":            "https://kitsu.app/anime/",
	"kurozora":         "https://kurozora.app/myanimelist.net/anime/",
	"letterboxd":       "https://letterboxd.com/tmdb/",
	"livechart":        "https://www.livechart.me/anime/",
	"myanili":          "https://myani.li/#/anime/details/",
	"myanimelist":      "https://myanimelist.net/anime/",
	"nautiljon":        "https://www.nautiljon.com/animes/",
	"notify":           "https://notify.moe/anime/",
	"otakotaku":        "https://otakotaku.com/anime/view/",
	"shikimori":        "https://shikimori.one/animes/",
	"shoboi":           "https://cal.syoboi.jp/tid/",
	"silveryasha":      "https://db.silveryasha.id/anime/",
	"simkl":            "https://simkl.com/anime/",
	"themoviedb":       "https://www.themoviedb.org/movie/",
	"trakt":            "https://trakt.tv/",
}

type ErrorResponse struct {
	Error   string `json:"error"`
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type StatusResponse struct {
	Status       string  `json:"status"`
	Code         int     `json:"code"`
	RequestTime  string  `json:"request_time"`
	ResponseTime string  `json:"response_time"`
	RequestEpoch float64 `json:"request_epoch"`
}

func init() {
	// Initialize Redis connection
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisAddr := os.Getenv("REDIS_ADDR")
		if redisAddr == "" {
			redisAddr = "localhost:6379"
		}
		rdb = redis.NewClient(&redis.Options{
			Addr:     redisAddr,
			Password: os.Getenv("REDIS_PASSWORD"),
			DB:       0,
		})
	} else {
		opt, _ := redis.ParseURL(redisURL)
		rdb = redis.NewClient(opt)
	}
}

func Handler(w http.ResponseWriter, r *http.Request) {
	// Enable CORS
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	w.Header().Set("Content-Type", "application/json")

	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}

	path := r.URL.Path
	startTime := time.Now()

	// Route handling
	switch {
	case path == "/":
		http.Redirect(w, r, "https://github.com/nattadasu/animeApi", http.StatusFound)
		return

	case path == "/status":
		handleStatus(w, r, startTime)
		return

	case path == "/heartbeat" || path == "/ping":
		handleHeartbeat(w, r, startTime)
		return

	case path == "/schema" || path == "/schema.json":
		handleSchema(w, r)
		return

	case path == "/updated":
		handleUpdated(w, r)
		return

	case path == "/robots.txt":
		w.Header().Set("Content-Type", "text/plain")
		w.Write([]byte("User-agent: *\nDisallow:"))
		return

	case path == "/favicon.ico":
		http.NotFound(w, r)
		return

	case strings.HasPrefix(path, "/trakt/"):
		handleTraktRoute(w, r)
		return

	case strings.HasPrefix(path, "/themoviedb/"):
		handleTMDBRoute(w, r)
		return

	case path == "/rd" || path == "/redirect":
		handleRedirect(w, r)
		return

	default:
		handlePlatformRoute(w, r, path)
	}
}

func resolvePlatform(platform string) string {
	platform = strings.ToLower(platform)
	lookup := make(map[string]string)
	for key, aliases := range platformSynonyms {
		lookup[key] = key
		for _, alias := range aliases {
			lookup[alias] = key
		}
	}
	if resolved, exists := lookup[platform]; exists {
		return resolved
	}
	return platform
}

func getAnimeData(platform, id string) (map[string]interface{}, error) {
	id = strings.TrimSuffix(id, ".json")
	id = strings.TrimSuffix(id, ".html")
	id, _ = url.QueryUnescape(id)

	platformKey := fmt.Sprintf("%s/%s", platform, id)
	internalIDStr, err := rdb.Get(ctx, platformKey).Result()
	if err != nil {
		return nil, err
	}

	internalID, err := strconv.ParseUint(internalIDStr, 10, 64)
	if err != nil {
		return nil, fmt.Errorf("invalid internal ID: %v", err)
	}

	animeDataStr, err := rdb.Get(ctx, fmt.Sprintf("%d", internalID)).Result()
	if err != nil {
		return nil, err
	}

	var animeData map[string]interface{}
	if err := json.Unmarshal([]byte(animeDataStr), &animeData); err != nil {
		return nil, err
	}

	return animeData, nil
}

func writeJSON(w http.ResponseWriter, data interface{}, status int) {
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, error string, code int, message string) {
	writeJSON(w, ErrorResponse{
		Error:   error,
		Code:    code,
		Message: message,
	}, code)
}

func handleStatus(w http.ResponseWriter, r *http.Request, startTime time.Time) {
	// Read status.json file
	statusFile, err := os.ReadFile("api/status.json")
	if err != nil {
		statusFile, err = os.ReadFile("status.json")
		if err != nil {
			writeJSON(w, map[string]string{
				"message": "Status endpoint - Redis-based implementation",
			}, http.StatusOK)
			return
		}
	}
	
	var statusData map[string]interface{}
	json.Unmarshal(statusFile, &statusData)
	writeJSON(w, statusData, http.StatusOK)
}

func handleHeartbeat(w http.ResponseWriter, r *http.Request, startTime time.Time) {
	start := time.Now()

	data, err := getAnimeData("myanimelist", "1")
	if err != nil {
		writeError(w, "Internal server error", 500, "Redis data is corrupted or unavailable")
		return
	}

	if malID, ok := data["myanimelist"]; !ok || malID != float64(1) {
		writeError(w, "Internal server error", 500, "Data integrity check failed")
		return
	}

	end := time.Now()
	requestTime := end.Sub(startTime).Seconds()
	responseTime := end.Sub(start).Seconds()

	writeJSON(w, StatusResponse{
		Status:       "OK",
		Code:         200,
		RequestTime:  fmt.Sprintf("%.3fs", requestTime),
		ResponseTime: fmt.Sprintf("%.3fs", responseTime),
		RequestEpoch: float64(startTime.Unix()),
	}, http.StatusOK)
}

func handleSchema(w http.ResponseWriter, r *http.Request) {
	// Read schema.json file
	schemaFile, err := os.ReadFile("api/schema.json")
	if err != nil {
		schemaFile, err = os.ReadFile("schema.json")
		if err != nil {
			writeJSON(w, map[string]string{
				"message": "Schema endpoint - file not found",
			}, http.StatusOK)
			return
		}
	}
	
	var schemaData map[string]interface{}
	json.Unmarshal(schemaFile, &schemaData)
	writeJSON(w, schemaData, http.StatusOK)
}

func handleUpdated(w http.ResponseWriter, r *http.Request) {
	// Read status.json and extract updated timestamp
	statusFile, _ := os.ReadFile("api/status.json")
	if statusFile == nil {
		statusFile, _ = os.ReadFile("status.json")
	}
	
	var statusData map[string]interface{}
	if err := json.Unmarshal(statusFile, &statusData); err == nil {
		if updated, ok := statusData["updated"].(map[string]interface{}); ok {
			if timestamp, ok := updated["timestamp"].(float64); ok {
				t := time.Unix(int64(timestamp), 0).UTC()
				formatted := t.Format("01/02/2006 15:04:05 MST")
				w.Header().Set("Content-Type", "text/plain")
				w.Write([]byte(fmt.Sprintf("Updated on %s", formatted)))
				return
			}
		}
	}
	
	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte("Updated endpoint - timestamp not available"))
}

func handleTraktRoute(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 3 {
		writeError(w, "Invalid request", 400, "Invalid Trakt URL format")
		return
	}

	mediaType := parts[1]
	mediaId := parts[2]
	var seasonId string

	if len(parts) > 4 && (parts[3] == "seasons" || parts[3] == "season") && len(parts) > 4 {
		seasonId = parts[4]
	}

	if seasonId == "0" && (mediaType == "show" || mediaType == "shows") {
		writeError(w, "Invalid season ID", 400, "Season ID cannot be 0")
		return
	}

	if !strings.HasSuffix(mediaType, "s") {
		mediaType = mediaType + "s"
	}

	var lookupKey string
	if seasonId == "" {
		lookupKey = fmt.Sprintf("%s/%s", mediaType, mediaId)
	} else {
		lookupKey = fmt.Sprintf("%s/%s/seasons/%s", mediaType, mediaId, seasonId)
	}

	data, err := getAnimeData("trakt", lookupKey)
	if err != nil {
		message := fmt.Sprintf("Media type %s with ID %s", mediaType, mediaId)
		if seasonId != "" {
			message += fmt.Sprintf(" and season ID %s", seasonId)
		}
		message += " not found"
		writeError(w, "Not found", 404, message)
		return
	}

	writeJSON(w, data, http.StatusOK)
}

func handleTMDBRoute(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(strings.Trim(r.URL.Path, "/"), "/")
	if len(parts) < 3 {
		writeError(w, "Invalid request", 400, "Invalid TMDB URL format")
		return
	}

	mediaType := parts[1]
	mediaId := parts[2]

	if mediaType == "tv" || (len(parts) > 3 && parts[3] == "season") {
		writeError(w, "Invalid request", 400, "Currently, only `movie` are supported")
		return
	}

	lookupKey := fmt.Sprintf("movie/%s", mediaId)
	data, err := getAnimeData("themoviedb", lookupKey)
	if err != nil {
		writeError(w, "Not found", 404, fmt.Sprintf("Media type %s with ID %s not found", mediaType, mediaId))
		return
	}

	writeJSON(w, data, http.StatusOK)
}

func handleRedirect(w http.ResponseWriter, r *http.Request) {
	query := r.URL.Query()
	
	platform := getQueryParam(query, []string{"platform", "from", "f"})
	platformID := getQueryParam(query, []string{"mediaid", "id", "i"})
	target := getQueryParam(query, []string{"target", "to", "t"})
	isRaw := getQueryParam(query, []string{"israw", "raw", "r"}) != ""

	if platform == "" {
		writeError(w, "Invalid platform", 400, "Platform not found, please specify platform by adding `platform` parameter.")
		return
	}

	if platformID == "" {
		writeError(w, "Invalid platform ID", 400, "Platform ID not found, please specify platform ID by adding `platform_id` parameter")
		return
	}

	platform = resolvePlatform(strings.ToLower(platform))
	if target != "" {
		target = resolvePlatform(strings.ToLower(target))
	}

	// Check for unsupported source platforms
	if platform == "kurozora" || platform == "myanili" || platform == "letterboxd" {
		writeError(w, "Invalid platform source", 400, fmt.Sprintf("Platform `%s` is not supported as redirect source (one-way)", platform))
		return
	}

	if target != "" && !isValidTarget(target) {
		writeError(w, "Invalid target", 400, fmt.Sprintf("Target %s not found", target))
		return
	}

	// Handle special cases for platform IDs
	if platform == "trakt" {
		if err := handleTraktCase(platformID); err != nil {
			writeError(w, "Invalid Trakt ID", 400, err.Error())
			return
		}
	}
	
	if platform == "themoviedb" && !strings.Contains(platformID, "movie") {
		platformID = "movie/" + platformID
	}

	data, err := getAnimeData(platform, platformID)
	if err != nil {
		writeError(w, "Not found", 404, fmt.Sprintf("Platform %s with ID %s not found", platform, platformID))
		return
	}

	if target == "" {
		uri := buildURI(platform, platformID)
		generateResponse(w, r, uri, isRaw)
		return
	}

	uri, err := buildTargetURI(target, data)
	if err != nil {
		title := "Unknown title"
		if t, ok := data["title"].(string); ok {
			title = t
		}
		writeError(w, "Not found", 404, fmt.Sprintf("%s does not exist on %s using %s with ID %s", title, target, platform, platformID))
		return
	}

	generateResponse(w, r, uri, isRaw)
}

func handlePlatformRoute(w http.ResponseWriter, r *http.Request, path string) {
	parts := strings.Split(strings.Trim(path, "/"), "/")
	
	if len(parts) == 1 {
		// Platform array route
		platform := parts[0]
		
		if strings.HasSuffix(path, ".tsv") {
			w.Header().Set("Content-Type", "text/tab-separated-values")
			w.Header().Set("Content-Disposition", "inline; filename=\"animeapi.tsv\"")
			w.Write([]byte("TSV endpoint - implement Redis-based TSV generation"))
			return
		}

		goto_ := getGoto(path, platform)
		if isValidTarget(strings.Replace(goto_, "_object", "", 1)) || platform == "animeapi" || platform == "aa" {
			githubURL := fmt.Sprintf("https://raw.githubusercontent.com/nattadasu/animeApi/v3/database/%s.json", goto_)
			http.Redirect(w, r, githubURL, http.StatusFound)
			return
		}

		writeError(w, "Invalid platform", 400, fmt.Sprintf("Platform %s not found, please check if it is a valid platform", platform))
		return
	}

	if len(parts) == 2 {
		// Platform lookup route
		platform := strings.ToLower(parts[0])
		platformID := parts[1]

		platform = resolvePlatform(platform)

		data, err := getAnimeData(platform, platformID)
		if err != nil {
			if err.Error() == "redis: nil" {
				writeError(w, "Not found", 404, fmt.Sprintf("Platform %s with ID %s not found", platform, platformID))
			} else {
				writeError(w, "Not found", 404, fmt.Sprintf("Platform %s not found or not supported", platform))
			}
			return
		}

		writeJSON(w, data, http.StatusOK)
		return
	}

	writeError(w, "Not found", 404, "Endpoint not found")
}

func getQueryParam(query url.Values, keys []string) string {
	for _, key := range keys {
		if val := query.Get(key); val != "" {
			return val
		}
	}
	return ""
}

func buildURI(platform, platformID string) string {
	if basePath, exists := routePaths[platform]; exists {
		return basePath + platformID
	}
	return ""
}

func generateResponse(w http.ResponseWriter, r *http.Request, uri string, isRaw bool) {
	if isRaw {
		w.Header().Set("Content-Type", "text/plain")
		w.Write([]byte(uri))
	} else {
		http.Redirect(w, r, uri, http.StatusFound)
	}
}

func handleTraktCase(platformID string) error {
	parts := strings.Split(platformID, "/")
	if len(parts) > 1 {
		if _, err := strconv.Atoi(parts[1]); err != nil {
			finalID := strings.Join(parts[:2], "/")
			return fmt.Errorf("Trakt ID for %s is not an `int`. Please convert the slug to `int` ID using Trakt API to proceed", finalID)
		}
	}
	return nil
}

func buildTargetURI(target string, maps map[string]interface{}) (string, error) {
	switch target {
	case "trakt":
		return buildTraktURI(maps)
	case "kurozora", "myanili":
		if malID, ok := maps["myanimelist"]; ok && malID != nil {
			return routePaths[target] + fmt.Sprintf("%v", malID), nil
		}
		return "", fmt.Errorf("MyAnimeList ID not found, which is requirement for %s", target)
	case "letterboxd":
		if tmdbID, ok := maps["themoviedb"]; ok && tmdbID != nil {
			return routePaths[target] + fmt.Sprintf("%v", tmdbID), nil
		}
		return "", fmt.Errorf("TheMovieDB ID not found, which is the main database source for Letterboxd")
	default:
		return buildGenericURI(maps, target)
	}
}

func buildTraktURI(maps map[string]interface{}) (string, error) {
	tgtID, ok := maps["trakt"]
	if !ok || tgtID == nil {
		return "", fmt.Errorf("trakt ID not found")
	}

	mediaType, _ := maps["trakt_type"].(string)
	season, _ := maps["trakt_season"]

	basePath := routePaths["trakt"]
	if season == nil {
		return fmt.Sprintf("%s%s/%v", basePath, mediaType, tgtID), nil
	}
	return fmt.Sprintf("%s%s/%v/seasons/%v", basePath, mediaType, tgtID, season), nil
}

func buildGenericURI(maps map[string]interface{}, target string) (string, error) {
	tgtID, ok := maps[target]
	if !ok || tgtID == nil {
		return "", fmt.Errorf("%s ID not found", target)
	}
	return routePaths[target] + fmt.Sprintf("%v", tgtID), nil
}

func isValidTarget(target string) bool {
	target = resolvePlatform(target)
	_, exists := platformSynonyms[target]
	return exists
}

func getGoto(route, rawPlatform string) string {
	goto_, _ := url.QueryUnescape(strings.Trim(route, "/"))
	rawPlatform, _ = url.QueryUnescape(rawPlatform)

	if strings.HasSuffix(goto_, ".json") {
		goto_ = goto_[:len(goto_)-5]
		rawPlatform = rawPlatform[:len(rawPlatform)-5]
	}

	isArray := strings.HasSuffix(rawPlatform, "()")
	rawPlatform = strings.TrimSuffix(rawPlatform, "()")
	goto_ = resolvePlatform(rawPlatform)
	goto_ = strings.Replace(goto_, "aa", "animeapi", 1)

	if !isArray && !strings.Contains(goto_, "animeapi") {
		goto_ = goto_ + "_object"
	}

	return goto_
}