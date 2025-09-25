using System.Collections.Generic;

namespace RayshiftTranslateFGO.Util
{
    public class AppNames
    {
        public static string[] ValidAppNames = new[]
        {
            "com.aniplex.fategrandorder",
            "io.rayshift.betterfgo",
        };

        public static Dictionary<string, string> AppDescriptions = new Dictionary<string, string>()
        {
            { "com.aniplex.fategrandorder", "Fate/Grand Order JP" },
            { "io.rayshift.betterfgo", "BetterFGO JP" }
        };
    }
}