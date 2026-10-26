using System;

public static class PojiaFixture
{
    public static uint Transform(uint input)
    {
        unchecked
        {
            uint value = input ^ 0xA53C91E7u;
            uint rotated = (value << 7) | (value >> 25);
            return rotated * 2654435761u + 17u;
        }
    }

    public static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--il")
        {
            byte[] il = typeof(PojiaFixture).GetMethod("Transform").GetMethodBody().GetILAsByteArray();
            Console.WriteLine(BitConverter.ToString(il).Replace("-", "").ToLowerInvariant());
            return 0;
        }
        string line;
        while ((line = Console.ReadLine()) != null)
        {
            uint input;
            if (!UInt32.TryParse(line, out input))
            {
                Console.WriteLine("INVALID");
                continue;
            }
            Console.WriteLine(Transform(input));
        }
        return 0;
    }
}
