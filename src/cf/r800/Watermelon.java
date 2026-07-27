package cf.r800;
import java.io.*;
public class Watermelon {
    public static void main(String[] a) throws IOException {
        int w = Integer.parseInt(new BufferedReader(new InputStreamReader(System.in)).readLine().trim());
        System.out.println((w > 2 && w % 2 == 0) ? "YES" : "NO");
    }
}
